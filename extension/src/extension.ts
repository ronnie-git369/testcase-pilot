// VS Code extension entrypoint — a thin client over the TestCasePilot backend.
//
// activate() is the COMPOSITION ROOT: it constructs the long-lived collaborators
// ONCE, registers the views/providers/commands, and lets context.subscriptions
// own their disposal. No feature logic lives here — just wiring.

import * as vscode from "vscode";

import { ApiClient } from "./api/ApiClient";
import { registerCommands } from "./commands";
import { SIDEBAR_VIEW_ID, SUPPORTED_LANGUAGES } from "./config/constants";
import { getApiUrl } from "./config/settings";
import { RequirementCodeLensProvider } from "./providers/RequirementCodeLensProvider";
import { SidebarViewProvider } from "./providers/SidebarViewProvider";
import { BackendService } from "./services/BackendService";
import { PipelineService } from "./services/PipelineService";
import { WorkspaceService } from "./services/WorkspaceService";
import { Logger } from "./utils/logger";
import { StatusBar } from "./utils/statusBar";

export function activate(context: vscode.ExtensionContext): void {
  const logger = new Logger();
  const statusBar = new StatusBar();

  // ApiClient resolves the base URL per request (the getter, not a snapshot), so
  // changing `testcasePilot.apiUrl` in Settings takes effect live.
  const backend = new BackendService(new ApiClient({ baseUrl: getApiUrl }));
  const pipeline = new PipelineService(backend);
  const workspace = new WorkspaceService();
  const sidebar = new SidebarViewProvider(
    context.extensionUri,
    logger,
    pipeline,
    statusBar,
    workspace
  );

  logger.info("TestCasePilot activated.");

  context.subscriptions.push(
    logger,
    statusBar,
    // Persistent sidebar; retainContextWhenHidden keeps its state across switches.
    vscode.window.registerWebviewViewProvider(SIDEBAR_VIEW_ID, sidebar, {
      webviewOptions: { retainContextWhenHidden: true },
    }),
    // CodeLens on requirement files (language-filtered at registration).
    vscode.languages.registerCodeLensProvider(
      SUPPORTED_LANGUAGES.map((language) => ({ language })),
      new RequirementCodeLensProvider()
    )
  );

  registerCommands(context, { backend, logger, statusBar, sidebar });

  // Fire-and-forget initial probe so the status bar reflects reality at startup.
  void backend
    .health()
    .then((ok) => (ok ? statusBar.connected() : statusBar.offline()));
}

export function deactivate(): void {
  // Disposables registered in context.subscriptions are released automatically.
}
