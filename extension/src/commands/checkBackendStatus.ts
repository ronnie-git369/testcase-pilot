// Command: "TestCasePilot: Check Backend Status".
//
// Pings GET /health and reflects the result in the status bar, a notification,
// and the log. This is the first command wired to the M3/M4 stack end-to-end.

import * as vscode from "vscode";

import { getApiUrl } from "../config/settings";
import type { CommandDeps } from "./types";

export async function checkBackendStatus(deps: CommandDeps): Promise<void> {
  const { backend, logger, statusBar } = deps;
  const url = getApiUrl();

  logger.request("GET", `${url}/health`);
  const connected = await backend.health();

  if (connected) {
    statusBar.connected();
    logger.info("Backend health: connected.");
    void vscode.window.showInformationMessage("TestCasePilot: backend connected.");
  } else {
    statusBar.offline();
    logger.error("Backend health: offline.");
    void vscode.window.showErrorMessage(
      `TestCasePilot: backend is offline at ${url}.`
    );
  }
}
