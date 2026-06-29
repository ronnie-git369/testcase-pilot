// A thin wrapper over a single StatusBarItem that reflects backend/pipeline
// state at a glance.
//
// Why a status bar: it gives persistent, low-friction feedback ("is the backend
// even up?", "is it still working?") without stealing focus the way a modal or
// repeated toast would. The text uses VS Code codicons ($(...)) so it renders
// crisply in any theme; `$(sync~spin)` animates.
//
// The click target (run "Check Backend Status") is wired in Milestone 4, once
// that command exists — leaving it unset here avoids a "command not found" click.

import * as vscode from "vscode";

import { COMMANDS } from "../config/constants";

export class StatusBar {
  private readonly item: vscode.StatusBarItem;

  constructor() {
    this.item = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      100
    );
    // Clicking the item runs the health check (registered in this milestone).
    this.item.command = COMMANDS.checkBackendStatus;
    this.idle();
    this.item.show();
  }

  idle(): void {
    this.set("$(beaker) TestCasePilot", "TestCasePilot");
  }

  connected(): void {
    this.set("$(check) TestCasePilot", "Backend connected");
  }

  offline(): void {
    this.set("$(error) TestCasePilot: offline", "Backend offline");
  }

  analyzing(): void {
    this.set("$(sync~spin) Analyzing…", "Analyzing requirement");
  }

  generating(): void {
    this.set("$(sync~spin) Generating…", "Generating test cases");
  }

  dispose(): void {
    this.item.dispose();
  }

  private set(text: string, tooltip: string): void {
    this.item.text = text;
    this.item.tooltip = tooltip;
  }
}
