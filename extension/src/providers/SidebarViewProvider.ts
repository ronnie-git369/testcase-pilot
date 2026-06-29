// The persistent sidebar — implements vscode.WebviewViewProvider.
//
// The host is the single source of truth. It owns the pipeline run, the live
// step statuses, and the last result; the webview only emits intents and renders
// what we post. Because we keep state HERE (not just in the webview), reopening
// the panel re-hydrates the last run.

import * as vscode from "vscode";

import {
  PIPELINE_STEPS,
  type AnalysisResult,
  type PipelineStep,
  type StepStatus,
} from "../models/pipeline";
import type {
  ExportFormat,
  HostToWebview,
  WebviewToHost,
} from "../models/messages";
import type { GenerationResult } from "../models/requirement";
import type { BackendService } from "../services/BackendService";
import { toJsonExport, toMarkdownExport } from "../services/exporter";
import type { PipelineService } from "../services/PipelineService";
import { renderReport } from "../services/render";
import type { WorkspaceService } from "../services/WorkspaceService";
import type { Logger } from "../utils/logger";
import type { StatusBar } from "../utils/statusBar";
import { renderSidebarHtml } from "../views/webviewHtml";

function freshStatuses(): Record<PipelineStep, StepStatus> {
  return {
    parser: "pending",
    rules: "pending",
    risk: "pending",
    rag: "pending",
    coverage: "pending",
    generate: "pending",
    review: "pending",
  };
}

export class SidebarViewProvider implements vscode.WebviewViewProvider {
  private view?: vscode.WebviewView;
  private busy = false;
  private lastResult?: AnalysisResult;
  private statuses: Record<PipelineStep, StepStatus> = freshStatuses();

  constructor(
    private readonly extensionUri: vscode.Uri,
    private readonly logger: Logger,
    private readonly pipeline: PipelineService,
    private readonly statusBar: StatusBar,
    private readonly workspace: WorkspaceService,
    private readonly backend: BackendService
  ) {}

  resolveWebviewView(webviewView: vscode.WebviewView): void {
    this.view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.extensionUri, "media")],
    };
    webviewView.webview.html = renderSidebarHtml(
      webviewView.webview,
      this.extensionUri
    );
    webviewView.webview.onDidReceiveMessage((message: WebviewToHost) =>
      this.onMessage(message)
    );
  }

  private post(message: HostToWebview): void {
    void this.view?.webview.postMessage(message);
  }

  /**
   * Public entry point for commands / CodeLens: load the given Markdown into the
   * sidebar and run the pipeline. The caller is responsible for revealing the
   * view first (e.g. via the `<viewId>.focus` command) so the webview exists.
   */
  public async analyzeMarkdown(markdown: string): Promise<void> {
    this.post({ type: "setMarkdown", markdown });
    await this.analyze(markdown);
  }

  private onMessage(message: WebviewToHost): void {
    switch (message.type) {
      case "ready":
        this.hydrate();
        break;
      case "analyze":
        void this.analyze(message.markdown);
        break;
      case "generate":
        void this.openReport();
        break;
      case "generatePlaywright":
        void this.generatePlaywright();
        break;
      case "useActiveEditor":
        this.useActiveEditor();
        break;
      case "export":
        void this.exportResult(message.format);
        break;
    }
  }

  /** Re-paint the current state when the webview (re)boots. */
  private hydrate(): void {
    this.post({
      type: "steps",
      steps: PIPELINE_STEPS.map((s) => ({
        key: s.key,
        label: s.label,
        status: this.statuses[s.key],
      })),
    });
    if (this.lastResult) {
      this.post({ type: "result", result: this.lastResult });
    }
    this.post({ type: "status", state: "idle" });
  }

  private async analyze(markdown: string): Promise<void> {
    if (this.busy) {
      return;
    }
    if (!markdown.trim()) {
      this.post({ type: "error", message: "Enter a requirement first." });
      return;
    }

    this.busy = true;
    this.statuses = freshStatuses();
    this.post({
      type: "steps",
      steps: PIPELINE_STEPS.map((s) => ({
        key: s.key,
        label: s.label,
        status: "pending",
      })),
    });
    this.post({ type: "status", state: "analyzing" });
    this.statusBar.analyzing();
    const stop = this.logger.time("sidebar.analyze");

    try {
      const result = await this.pipeline.analyze(markdown, (event) => {
        this.statuses[event.step] = event.status;
        this.post({
          type: "stepUpdate",
          step: event.step,
          status: event.status,
          durationMs: event.durationMs,
          message: event.message,
        });
      });

      this.lastResult = result;
      this.post({ type: "result", result });
      this.post({ type: "status", state: "idle" });
      this.statusBar.connected();
      this.logger.info(
        `Sidebar: analyzed "${result.requirement.feature}" -> ${result.testCases.length} cases.`
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.logger.error(`Sidebar analyze failed: ${message}`);
      this.post({ type: "error", message });
      this.post({ type: "status", state: "idle" });
      this.statusBar.offline();
    } finally {
      stop();
      this.busy = false;
    }
  }

  /** Open the last analysis as a Markdown report in an editor tab. */
  private async openReport(): Promise<void> {
    if (!this.lastResult) {
      this.post({ type: "log", text: "Run Analyze first." });
      return;
    }
    const generation: GenerationResult = {
      requirement: this.lastResult.requirement,
      coverage: this.lastResult.coverage,
      test_cases: this.lastResult.testCases,
    };
    const doc = await vscode.workspace.openTextDocument({
      language: "markdown",
      content: renderReport(generation),
    });
    await vscode.window.showTextDocument(doc, { preview: false });
  }

  /** Pull the active editor's text (selection or whole doc) into the textarea. */
  private useActiveEditor(): void {
    const text = this.workspace.getActiveText();
    if (text === undefined) {
      this.post({ type: "log", text: "No active editor." });
      return;
    }
    this.post({ type: "setMarkdown", markdown: text });
  }

  /** Render a Playwright spec (backend codegen) and save it to tests/e2e/. */
  private async generatePlaywright(): Promise<void> {
    if (!this.lastResult) {
      this.post({ type: "log", text: "Run Analyze first." });
      return;
    }
    this.post({ type: "log", text: "Generating Playwright spec…" });
    try {
      const spec = await this.backend.playwright(
        this.lastResult.requirement.feature,
        this.lastResult.testCases
      );
      const uri = await this.workspace.saveArtifact(
        spec.filename,
        spec.code,
        "tests/e2e"
      );
      if (uri) {
        this.logger.info(`Playwright spec -> ${uri.fsPath}`);
        this.post({ type: "log", text: `Saved ${spec.filename}` });
        void vscode.window.showInformationMessage(
          `TestCasePilot: saved ${vscode.workspace.asRelativePath(uri)}.`
        );
      } else {
        this.post({ type: "log", text: "Export cancelled." });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.logger.error(`Playwright generation failed: ${message}`);
      this.post({ type: "error", message });
    }
  }

  /** Export the last analysis to a Markdown or JSON file (with confirmation). */
  private async exportResult(format: ExportFormat): Promise<void> {
    if (!this.lastResult) {
      this.post({ type: "log", text: "Run Analyze first." });
      return;
    }
    const payload =
      format === "json"
        ? toJsonExport(this.lastResult)
        : toMarkdownExport(this.lastResult);

    const uri = await this.workspace.saveArtifact(
      payload.fileName,
      payload.content
    );
    if (uri) {
      this.logger.info(`Exported ${format} -> ${uri.fsPath}`);
      this.post({ type: "log", text: `Saved ${payload.fileName}` });
      void vscode.window.showInformationMessage(
        `TestCasePilot: saved ${vscode.workspace.asRelativePath(uri)}.`
      );
    } else {
      this.post({ type: "log", text: "Export cancelled." });
    }
  }
}
