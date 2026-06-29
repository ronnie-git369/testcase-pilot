// Centralized identifiers and static configuration.
//
// Every "magic string" the extension needs — command IDs, the settings section,
// view IDs, the output-channel name — lives here ONCE. The rest of the codebase
// imports these symbols instead of retyping literals, so a rename is a one-line
// change and a typo is a compile error, not a silent no-op at runtime.

export const CONFIG_SECTION = "testcasePilot";

export const DEFAULT_API_URL = "http://127.0.0.1:8000";

export const OUTPUT_CHANNEL_NAME = "TestCasePilot Output";

export const SIDEBAR_VIEW_ID = "testcasePilot.sidebar";

// Document languages we treat as "requirement files" (CodeLens, context menu).
export const SUPPORTED_LANGUAGES = ["markdown", "plaintext"] as const;

// Command IDs — these MUST match package.json `contributes.commands[].command`.
// Some are registered in later milestones; defined here so call sites are typed.
export const COMMANDS = {
  generate: "testcasePilot.generate",
  newRequirement: "testcasePilot.newRequirement",
  analyzeRequirement: "testcasePilot.analyzeRequirement",
  openSidebar: "testcasePilot.openSidebar",
  checkBackendStatus: "testcasePilot.checkBackendStatus",
} as const;
