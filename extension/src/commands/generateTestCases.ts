// Command: "TestCasePilot: Generate Test Cases".
//
// Reads the active editor (selection or whole document), runs the full pipeline
// via BackendService, and opens the rendered Markdown report. Now routed through
// the typed facade + logger + status bar (was the temporary generateClient).
// Milestone 8 extends this with context-menu / CodeLens entry points.

import * as vscode from "vscode";

import { renderReport } from "../services/render";
import type { CommandDeps } from "./types";

export async function runGenerate(deps: CommandDeps): Promise<void> {
  const { backend, logger, statusBar } = deps;

  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showErrorMessage(
      "TestCasePilot: open a requirement file first."
    );
    return;
  }

  const { selection, document } = editor;
  const markdown = selection.isEmpty
    ? document.getText()
    : document.getText(selection);

  if (!markdown.trim()) {
    vscode.window.showErrorMessage("TestCasePilot: the requirement is empty.");
    return;
  }

  const stop = logger.time("generate");
  statusBar.generating();

  try {
    const result = await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: "TestCasePilot: generating test cases…",
      },
      () => backend.generate(markdown)
    );

    const doc = await vscode.workspace.openTextDocument({
      language: "markdown",
      content: renderReport(result),
    });
    await vscode.window.showTextDocument(doc, { preview: false });
    logger.info(`Generated ${result.test_cases.length} test cases.`);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    logger.error(message);
    vscode.window.showErrorMessage(`TestCasePilot: ${message}`);
  } finally {
    stop();
    statusBar.idle();
  }
}
