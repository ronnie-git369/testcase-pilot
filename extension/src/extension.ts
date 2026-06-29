// VS Code extension entrypoint — a thin client over the TestCasePilot backend.
//
// activate() is the COMPOSITION ROOT: it constructs the long-lived collaborators
// (transport, service, logger, status bar) ONCE, hands them to the command
// registrar, and lets context.subscriptions own their disposal. No feature logic
// lives here — just wiring.

import * as vscode from "vscode";

import { ApiClient } from "./api/ApiClient";
import { registerCommands } from "./commands";
import { getApiUrl } from "./config/settings";
import { BackendService } from "./services/BackendService";
import { Logger } from "./utils/logger";
import { StatusBar } from "./utils/statusBar";

export function activate(context: vscode.ExtensionContext): void {
  const logger = new Logger();
  const statusBar = new StatusBar();

  // ApiClient resolves the base URL per request (passing the getter, not a
  // snapshot), so changing `testcasePilot.apiUrl` in Settings takes effect live.
  const backend = new BackendService(new ApiClient({ baseUrl: getApiUrl }));

  logger.info("TestCasePilot activated.");
  context.subscriptions.push(logger, statusBar);

  registerCommands(context, { backend, logger, statusBar });

  // Fire-and-forget initial probe so the status bar reflects reality at startup
  // (no toast — that's reserved for the explicit "Check Backend Status" command).
  void backend
    .health()
    .then((ok) => (ok ? statusBar.connected() : statusBar.offline()));
}

export function deactivate(): void {
  // Disposables registered in context.subscriptions are released automatically.
}
