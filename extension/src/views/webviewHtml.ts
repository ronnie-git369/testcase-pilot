// Assembles the sidebar's HTML host-side: injects the CSP + nonce and rewrites
// the css/js paths to webview-safe URIs.
//
// The browser assets live in media/ (NOT bundled by esbuild — they run in the
// webview, not Node). `asWebviewUri` turns a disk path into the special
// vscode-webview:// URI the sandbox can load, and `localResourceRoots` (set on
// the webview) restricts loads to media/. The nonce ties the CSP to our one
// <script>, so no injected script can execute.

import * as vscode from "vscode";

import { makeNonce } from "../utils/nonce";

export function renderSidebarHtml(
  webview: vscode.Webview,
  extensionUri: vscode.Uri
): string {
  const nonce = makeNonce();
  const media = vscode.Uri.joinPath(extensionUri, "media");
  const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(media, "sidebar.css"));
  const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(media, "sidebar.js"));

  const csp = [
    "default-src 'none'",
    `style-src ${webview.cspSource}`,
    `font-src ${webview.cspSource}`,
    `script-src 'nonce-${nonce}'`,
  ].join("; ");

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy" content="${csp}" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link href="${styleUri}" rel="stylesheet" />
  <title>TestCasePilot</title>
</head>
<body>
  <section class="block">
    <h2>Requirement</h2>
    <textarea id="requirement" placeholder="Paste a requirement, or click 'Use active editor'."></textarea>
    <div class="row">
      <button id="use-editor" class="ghost">Use active editor</button>
      <button id="analyze" class="primary">Analyze</button>
    </div>
  </section>

  <section class="block">
    <h2>Agent Pipeline</h2>
    <ul id="pipeline"></ul>
  </section>

  <section class="block">
    <h2>Results</h2>
    <div id="results"><p class="muted">Run Analyze to see results.</p></div>
  </section>

  <section class="block">
    <h2>Generate</h2>
    <div class="row wrap">
      <button id="gen-tests" class="ghost">Generate Test Cases</button>
      <button id="gen-playwright" class="ghost" disabled title="Coming soon (M11)">Generate Playwright Tests</button>
      <button id="export-md" class="ghost">Export Markdown</button>
      <button id="export-json" class="ghost">Export JSON</button>
    </div>
  </section>

  <div id="status" class="muted"></div>

  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
}
