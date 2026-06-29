// Typed accessors for the extension's user settings.
//
// Why a module instead of calling vscode.workspace.getConfiguration() inline
// everywhere: one place knows the setting KEYS and their defaults, so the rest
// of the code asks getApiUrl() (typed, defaulted) rather than juggling string
// keys and `| undefined`. Settings are read fresh on each call so changes in the
// Settings UI take effect without reload.

import * as vscode from "vscode";

import { CONFIG_SECTION, DEFAULT_API_URL } from "./constants";

function config(): vscode.WorkspaceConfiguration {
  return vscode.workspace.getConfiguration(CONFIG_SECTION);
}

export function getApiUrl(): string {
  return config().get<string>("apiUrl", DEFAULT_API_URL);
}

/** Preferred AI provider hint forwarded to the backend ("auto" lets it decide). */
export function getDefaultProvider(): string {
  return config().get<string>("defaultProvider", "auto");
}

export function isAutoAnalyze(): boolean {
  return config().get<boolean>("autoAnalyze", false);
}

export function areLogsEnabled(): boolean {
  return config().get<boolean>("enableLogs", true);
}
