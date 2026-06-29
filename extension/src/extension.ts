// VS Code extension entrypoint — a thin client over the TestCasePilot backend.
//
// activate() is the COMPOSITION ROOT: it constructs the long-lived collaborators
// ONCE, registers the views/providers/commands, and lets context.subscriptions
// own their disposal. No feature logic lives here — just wiring.

import * as vscode from "vscode";

import { ApiClient } from "./api/ApiClient";
import { registerCommands } from "./commands";
import {
  CONFIG_SECTION,
  SIDEBAR_VIEW_ID,
  SUPPORTED_LANGUAGES,
} from "./config/constants";
import { getApiUrl, getDefaultProvider, isAutoAnalyze } from "./config/settings";
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
  const backend = new BackendService(
    new ApiClient({ baseUrl: getApiUrl }),
    getDefaultProvider
  );
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

  context.subscriptions.push(
    // Auto-analyze a requirement file on save, when the setting is enabled.
    vscode.workspace.onDidSaveTextDocument(async (document) => {
      if (!isAutoAnalyze()) {
        return;
      }
      if (!(SUPPORTED_LANGUAGES as readonly string[]).includes(document.languageId)) {
        return;
      }
      const text = document.getText();
      if (!/^#\s/m.test(text)) {
        return; // only files that look like a requirement (have an H1)
      }
      await vscode.commands.executeCommand(`${SIDEBAR_VIEW_ID}.focus`);
      await sidebar.analyzeMarkdown(text);
    }),
    // Re-probe the backend when the API URL changes, so the status bar stays true.
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (event.affectsConfiguration(`${CONFIG_SECTION}.apiUrl`)) {
        logger.info("apiUrl changed; re-checking backend health.");
        void backend
          .health()
          .then((ok) => (ok ? statusBar.connected() : statusBar.offline()));
      }
    })
  );

  // Fire-and-forget initial probe so the status bar reflects reality at startup.
  void backend
    .health()
    .then((ok) => (ok ? statusBar.connected() : statusBar.offline()));
}

export function deactivate(): void {
  // Disposables registered in context.subscriptions are released automatically.
}
