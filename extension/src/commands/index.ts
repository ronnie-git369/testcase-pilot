// Central command registration.
//
// One place that maps command IDs (constants) to handlers and pushes the
// disposables onto context.subscriptions. Each milestone adds a line here, not a
// new wiring block, so the entrypoint stays a thin composition root.

import * as vscode from "vscode";

import { COMMANDS } from "../config/constants";
import { RequirementPanel } from "../views/RequirementPanel";
import { analyzeRequirement } from "./analyzeRequirement";
import { checkBackendStatus } from "./checkBackendStatus";
import { runGenerate } from "./generateTestCases";
import { openSidebar } from "./openSidebar";
import type { CommandDeps } from "./types";

export type { CommandDeps } from "./types";

export function registerCommands(
  context: vscode.ExtensionContext,
  deps: CommandDeps
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(COMMANDS.analyzeRequirement, () =>
      analyzeRequirement(deps)
    ),
    vscode.commands.registerCommand(COMMANDS.generate, () => runGenerate(deps)),
    vscode.commands.registerCommand(COMMANDS.openSidebar, () => openSidebar()),
    vscode.commands.registerCommand(COMMANDS.newRequirement, () =>
      RequirementPanel.show()
    ),
    vscode.commands.registerCommand(COMMANDS.checkBackendStatus, () =>
      checkBackendStatus(deps)
    )
  );
}
