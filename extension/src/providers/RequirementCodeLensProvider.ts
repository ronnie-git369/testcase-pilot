// CodeLens above requirement files: actionable links rendered inline at the top
// of the document.
//
// A CodeLens is a {range, command} pair VS Code renders as a clickable label in
// the editor. We surface three at line 0 — Analyze, Generate Tests, Open Results
// — but ONLY when the document looks like a requirement (has a top-level "# "
// heading), so we don't clutter every Markdown/plaintext file. The language
// filter is applied at registration (see extension.ts).

import * as vscode from "vscode";

import { COMMANDS } from "../config/constants";

export class RequirementCodeLensProvider implements vscode.CodeLensProvider {
  provideCodeLenses(document: vscode.TextDocument): vscode.CodeLens[] {
    // Heuristic: a requirement has at least one H1. Avoids noise on prose files.
    if (!/^#\s/m.test(document.getText())) {
      return [];
    }

    const top = new vscode.Range(0, 0, 0, 0);
    return [
      new vscode.CodeLens(top, {
        title: "$(beaker) Analyze Requirement",
        command: COMMANDS.analyzeRequirement,
      }),
      new vscode.CodeLens(top, {
        title: "Generate Tests",
        command: COMMANDS.generate,
      }),
      new vscode.CodeLens(top, {
        title: "Open Results",
        command: COMMANDS.openSidebar,
      }),
    ];
  }
}
