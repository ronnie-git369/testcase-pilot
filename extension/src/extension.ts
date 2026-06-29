// VS Code extension entrypoint — a thin client over the TestCasePilot backend.
//
// activate() is the COMPOSITION ROOT: it constructs the long-lived singletons
// (logger, status bar), wires command handlers to them, and registers every
// disposable with context.subscriptions so VS Code tears them down on unload.
// Keeping construction here (not scattered in modules) keeps dependencies
// explicit and testable.

import * as vscode from "vscode";

import { generateTestCases } from "./api/generateClient";
import { COMMANDS } from "./config/constants";
import { getApiUrl } from "./config/settings";
import { renderReport } from "./services/render";
import { Logger } from "./utils/logger";
import { StatusBar } from "./utils/statusBar";
import { RequirementPanel } from "./views/RequirementPanel";

export function activate(context: vscode.ExtensionContext): void {
  const logger = new Logger();
  const statusBar = new StatusBar();
  logger.info("TestCasePilot activated.");

  context.subscriptions.push(
    logger,
    statusBar,
    vscode.commands.registerCommand(COMMANDS.generate, () =>
      runGenerate(logger, statusBar)
    ),
    vscode.commands.registerCommand(COMMANDS.newRequirement, () =>
      RequirementPanel.show()
    )
  );
}

export function deactivate(): void {
  // Disposables registered in context.subscriptions are released automatically.
}

async function runGenerate(logger: Logger, statusBar: StatusBar): Promise<void> {
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

  const apiUrl = getApiUrl();
  const stop = logger.time("generate");
  logger.request("POST", `${apiUrl}/requirements/generate`);
  statusBar.generating();

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
