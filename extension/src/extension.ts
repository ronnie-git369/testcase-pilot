// VS Code extension entrypoint — a thin client over the TestCasePilot backend.

import * as vscode from "vscode";

import { generateTestCases } from "./api";
import { renderReport } from "./render";

export function activate(context: vscode.ExtensionContext): void {
  context.subscriptions.push(
    vscode.commands.registerCommand("testcasePilot.generate", runGenerate)
  );
}

export function deactivate(): void {
  // nothing to clean up
}

async function runGenerate(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showErrorMessage(
      "TestCasePilot: open a requirement file first."
    );
    return;
  }

  // Use the selection if there is one, otherwise the whole document.
  const { selection, document } = editor;
  const markdown = selection.isEmpty
    ? document.getText()
    : document.getText(selection);

  if (!markdown.trim()) {
    vscode.window.showErrorMessage("TestCasePilot: the requirement is empty.");
    return;
  }

  const apiUrl = vscode.workspace
    .getConfiguration("testcasePilot")
    .get<string>("apiUrl", "http://127.0.0.1:8000");

  try {
    const result = await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: "TestCasePilot: generating test cases…",
      },
      () => generateTestCases(apiUrl, markdown)
    );

    const doc = await vscode.workspace.openTextDocument({
      language: "markdown",
      content: renderReport(result),
    });
    await vscode.window.showTextDocument(doc, { preview: false });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    vscode.window.showErrorMessage(`TestCasePilot: ${message}`);
  }
}
