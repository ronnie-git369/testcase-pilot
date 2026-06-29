// The persistent sidebar — implements vscode.WebviewViewProvider.
//
// VS Code calls resolveWebviewView() when the view first becomes visible. We set
// the webview options (scripts on, resources confined to media/), inject the
// HTML, and wire the two-way message channel. The host is the single source of
// truth; the webview only emits intents and renders what we post.
//
// M6 is the SHELL: it renders the layout and round-trips messages (logging
// them). Milestone 7 injects PipelineService and drives the live steps/results.

import * as vscode from "vscode";

import { PIPELINE_STEPS } from "../models/pipeline";
import type { HostToWebview, WebviewToHost } from "../models/messages";
import type { Logger } from "../utils/logger";
import { renderSidebarHtml } from "../views/webviewHtml";

export class SidebarViewProvider implements vscode.WebviewViewProvider {
  private view?: vscode.WebviewView;

  constructor(
    private readonly extensionUri: vscode.Uri,
    private readonly logger: Logger
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

  private onMessage(message: WebviewToHost): void {
    switch (message.type) {
      case "ready":
        // The webview booted: paint the initial (all-pending) pipeline.
        this.logger.info("Sidebar ready.");
        this.post({
          type: "steps",
          steps: PIPELINE_STEPS.map((s) => ({
            key: s.key,
            label: s.label,
            status: "pending",
          })),
        });
        this.post({ type: "status", state: "idle" });
        break;

      case "analyze":
        this.logger.info(
          `Sidebar: analyze requested (${message.markdown.length} chars).`
        );
        this.post({
          type: "log",
          text: "Analyze received by host (live pipeline lands in M7).",
        });
        break;

      default:
        this.logger.info(`Sidebar: '${message.type}' received (not yet wired).`);
    }
  }
}
