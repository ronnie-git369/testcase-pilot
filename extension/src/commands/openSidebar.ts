// Command: "TestCasePilot: Open Sidebar".
//
// Focuses the sidebar view. VS Code auto-generates a `<viewId>.focus` command
// for every contributed view, so we simply delegate to it.

import * as vscode from "vscode";

import { SIDEBAR_VIEW_ID } from "../config/constants";

export async function openSidebar(): Promise<void> {
  await vscode.commands.executeCommand(`${SIDEBAR_VIEW_ID}.focus`);
}
