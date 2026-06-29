// Command: "TestCasePilot: Analyze Requirement".
//
// Reads the active editor (selection or whole document), reveals the sidebar,
// and runs the live pipeline there. Shared by the Command Palette and the
// CodeLens "Analyze Requirement" action.

import * as vscode from "vscode";

import { SIDEBAR_VIEW_ID } from "../config/constants";
import type { CommandDeps } from "./types";

export async function analyzeRequirement(deps: CommandDeps): Promise<void> {
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

  // Reveal the sidebar (resolves the webview if it isn't open yet), then run.
  await vscode.commands.executeCommand(`${SIDEBAR_VIEW_ID}.focus`);
  await deps.sidebar.analyzeMarkdown(markdown);
}
