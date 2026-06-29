// Webview UI for composing a requirement and generating test cases.
//
// A singleton panel that hosts a themed HTML form (Feature, User story, and an
// add-a-line Acceptance criteria list). On submit it composes Markdown, posts it
// to the backend via the shared api client, opens the rendered report beside the
// form, and echoes a result summary back into the panel. All vscode-specific
// wiring lives here; the form->Markdown logic stays pure in services/compose.ts.
//
// NOTE (migration): in Milestone 6 this transient WebviewPanel is replaced by a
// persistent sidebar WebviewView (providers/SidebarViewProvider.ts). It is kept
// working here so the scaffold migration changes structure, not behavior.

import * as vscode from "vscode";

import { generateTestCases } from "../api/generateClient";
import type { GenerationResult } from "../models/requirement";
import { buildRequirementMarkdown, type RequirementInput } from "../services/compose";
import { renderReport } from "../services/render";
import { makeNonce } from "../utils/nonce";

export class RequirementPanel {
  public static readonly viewType = "testcasePilot.form";
  private static current: RequirementPanel | undefined;

  private readonly panel: vscode.WebviewPanel;
  private readonly disposables: vscode.Disposable[] = [];

  /** Reveal the existing panel, or create one if none is open. */
  public static show(): void {
    const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;

    if (RequirementPanel.current) {
      RequirementPanel.current.panel.reveal(column);
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      RequirementPanel.viewType,
      "TestCasePilot",
      column,
      { enableScripts: true, retainContextWhenHidden: true }
    );
    RequirementPanel.current = new RequirementPanel(panel);
  }

  private constructor(panel: vscode.WebviewPanel) {
    this.panel = panel;
    this.panel.webview.html = this.html(panel.webview);

    this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
    this.panel.webview.onDidReceiveMessage(
      (message) => this.onMessage(message),
      null,
      this.disposables
    );
  }

  private async onMessage(message: { type?: string; input?: RequirementInput }): Promise<void> {
    if (message?.type !== "generate" || !message.input) {
      return;
    }

    const input = message.input;
    if (!input.feature.trim()) {
      this.post({ type: "error", message: "Feature is required." });
      return;
    }

    const apiUrl = vscode.workspace
      .getConfiguration("testcasePilot")
      .get<string>("apiUrl", "http://127.0.0.1:8000");

    const markdown = buildRequirementMarkdown(input);
    this.post({ type: "busy" });

    try {
      const result = await generateTestCases(apiUrl, markdown);

      const doc = await vscode.workspace.openTextDocument({
        language: "markdown",
        content: renderReport(result),
      });
      await vscode.window.showTextDocument(doc, {
        preview: false,
        viewColumn: vscode.ViewColumn.Beside,
      });

      this.post({ type: "result", result });
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      this.post({ type: "error", message: detail });
    }
  }

  private post(message: { type: string; message?: string; result?: GenerationResult }): void {
    void this.panel.webview.postMessage(message);
  }

  private dispose(): void {
    RequirementPanel.current = undefined;
    this.panel.dispose();
    while (this.disposables.length) {
      this.disposables.pop()?.dispose();
    }
  }

  private html(webview: vscode.Webview): string {
    const nonce = makeNonce();
    const csp = [
      "default-src 'none'",
      `style-src ${webview.cspSource} 'unsafe-inline'`,
      `script-src 'nonce-${nonce}'`,
    ].join("; ");

    return /* html */ `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy" content="${csp}" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>TestCasePilot</title>
  <style>
    body { font-family: var(--vscode-font-family); color: var(--vscode-foreground);
      padding: 0 4px 24px; font-size: var(--vscode-font-size); }
    h1 { font-size: 1.3em; margin: 16px 0 4px; }
    p.sub { color: var(--vscode-descriptionForeground); margin: 0 0 16px; }
    label { display: block; font-weight: 600; margin: 14px 0 4px; }
    input[type=text], textarea {
      width: 100%; box-sizing: border-box; padding: 6px 8px;
      color: var(--vscode-input-foreground); background: var(--vscode-input-background);
      border: 1px solid var(--vscode-input-border, transparent); border-radius: 2px;
      font-family: inherit; font-size: inherit; }
    textarea { resize: vertical; min-height: 48px; }
    .crit-row { display: flex; gap: 6px; margin-bottom: 6px; }
    .crit-row input { flex: 1; }
    button { font-family: inherit; font-size: inherit; cursor: pointer;
      border: none; border-radius: 2px; padding: 6px 12px; }
    button.primary { color: var(--vscode-button-foreground);
      background: var(--vscode-button-background); margin-top: 18px; }
    button.primary:hover { background: var(--vscode-button-hoverBackground); }
    button.primary:disabled { opacity: .5; cursor: default; }
    button.ghost { color: var(--vscode-button-secondaryForeground, var(--vscode-foreground));
      background: var(--vscode-button-secondaryBackground, transparent);
      border: 1px solid var(--vscode-input-border, var(--vscode-foreground)); }
    .icon-btn { background: transparent; color: var(--vscode-foreground);
      border: 1px solid var(--vscode-input-border, var(--vscode-foreground));
      width: 30px; }
    #status { margin-top: 14px; min-height: 1.2em; }
    #status.error { color: var(--vscode-errorForeground); }
    #results { margin-top: 18px; }
    .case { border-left: 3px solid var(--vscode-textLink-foreground);
      padding: 4px 10px; margin: 8px 0; background: var(--vscode-textBlockQuote-background); }
    .case .meta { color: var(--vscode-descriptionForeground); font-size: .9em; }
    .tag { display: inline-block; padding: 0 6px; border-radius: 8px; font-size: .8em;
      background: var(--vscode-badge-background); color: var(--vscode-badge-foreground); }
  </style>
</head>
<body>
  <h1>Generate Test Cases</h1>
  <p class="sub">Describe the requirement; the backend runs the full pipeline and returns review-ready test cases.</p>

  <label for="feature">Feature <span aria-hidden="true">*</span></label>
  <input type="text" id="feature" placeholder="e.g. Password Reset" />

  <label for="story">User story <span style="font-weight:400;color:var(--vscode-descriptionForeground)">(optional)</span></label>
  <textarea id="story" placeholder="As a user I want to reset my password so that I can regain access."></textarea>

  <label>Acceptance criteria <span style="font-weight:400;color:var(--vscode-descriptionForeground)">(one per line)</span></label>
  <div id="criteria"></div>
  <button type="button" class="ghost" id="add-crit">+ Add criterion</button>

  <div>
    <button type="button" class="primary" id="generate">Generate test cases</button>
  </div>

  <div id="status"></div>
  <div id="results"></div>

  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    const critList = document.getElementById("criteria");
    const statusEl = document.getElementById("status");
    const resultsEl = document.getElementById("results");
    const generateBtn = document.getElementById("generate");

    function addCriterion(value) {
      const row = document.createElement("div");
      row.className = "crit-row";
      const input = document.createElement("input");
      input.type = "text";
      input.placeholder = "e.g. The reset link expires after 30 minutes";
      if (value) input.value = value;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "icon-btn";
      remove.textContent = "✕";
      remove.title = "Remove";
      remove.addEventListener("click", () => {
        row.remove();
        if (!critList.children.length) addCriterion("");
      });
      row.append(input, remove);
      critList.append(row);
      input.focus();
    }

    document.getElementById("add-crit").addEventListener("click", () => addCriterion(""));
    addCriterion("");

    function setBusy(busy) {
      generateBtn.disabled = busy;
      generateBtn.textContent = busy ? "Generating…" : "Generate test cases";
    }

    function escapeHtml(s) {
      return String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
    }

    function renderResult(result) {
      const cases = result.test_cases || [];
      const parts = ['<h1>' + cases.length + ' test case' + (cases.length === 1 ? '' : 's') + '</h1>'];
      parts.push('<p class="sub">Full report opened beside this panel.</p>');
      for (const c of cases) {
        parts.push(
          '<div class="case"><strong>' + escapeHtml(c.title) + '</strong> ' +
          '<span class="tag">' + escapeHtml(c.type) + '</span> ' +
          '<span class="tag">' + escapeHtml(c.priority) + '</span>' +
          (c.covers ? '<div class="meta">Covers: ' + escapeHtml(c.covers) + '</div>' : '') +
          '</div>'
        );
      }
      resultsEl.innerHTML = parts.join("");
    }

    generateBtn.addEventListener("click", () => {
      const feature = document.getElementById("feature").value;
      const userStory = document.getElementById("story").value;
      const acceptanceCriteria = Array.from(critList.querySelectorAll("input")).map((i) => i.value);

      if (!feature.trim()) {
        statusEl.className = "error";
        statusEl.textContent = "Feature is required.";
        return;
      }
      statusEl.className = "";
      statusEl.textContent = "";
      resultsEl.innerHTML = "";
      setBusy(true);
      vscode.postMessage({ type: "generate", input: { feature, userStory, acceptanceCriteria } });
    });

    window.addEventListener("message", (event) => {
      const msg = event.data;
      if (msg.type === "busy") {
        statusEl.className = "";
        statusEl.textContent = "Generating test cases…";
      } else if (msg.type === "error") {
        setBusy(false);
        statusEl.className = "error";
        statusEl.textContent = "Error: " + msg.message;
      } else if (msg.type === "result") {
        setBusy(false);
        statusEl.textContent = "";
        renderResult(msg.result);
      }
    });
  </script>
</body>
</html>`;
  }
}
