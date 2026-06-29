// Browser-side controller for the sidebar webview.
//
// This runs in the webview sandbox (NOT Node) — no imports, no backend access.
// It is a PURE PROJECTION: it emits intents to the host (postMessage) and
// renders the state the host posts back. All logic and all network calls live
// host-side. CSP blocks this script from reaching the backend directly.

(function () {
  const vscode = acquireVsCodeApi();
  const byId = (id) => document.getElementById(id);

  const requirementEl = byId("requirement");
  const pipelineEl = byId("pipeline");
  const resultsEl = byId("results");
  const statusEl = byId("status");

  // Persist the textarea draft across webview reloads.
  const saved = vscode.getState();
  if (saved && saved.markdown) {
    requirementEl.value = saved.markdown;
  }
  requirementEl.addEventListener("input", () => {
    vscode.setState({ markdown: requirementEl.value });
  });

  const ICON = { pending: "○", running: "◐", done: "✓", error: "✕" };

  function esc(s) {
    return String(s).replace(
      /[&<>]/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])
    );
  }

  function renderSteps(steps) {
    pipelineEl.innerHTML = "";
    for (const s of steps) {
      const li = document.createElement("li");
      li.dataset.step = s.key;
      li.innerHTML =
        '<span class="step-icon step-' + s.status + '">' + ICON[s.status] + "</span>" +
        "<span>" + esc(s.label) + "</span>" +
        '<span class="step-dur"></span>';
      pipelineEl.appendChild(li);
    }
  }

  function updateStep(step, status, durationMs) {
    const li = pipelineEl.querySelector('li[data-step="' + step + '"]');
    if (!li) return;
    const icon = li.querySelector(".step-icon");
    icon.className = "step-icon step-" + status;
    icon.textContent = ICON[status];
    if (durationMs != null) {
      li.querySelector(".step-dur").textContent = (durationMs / 1000).toFixed(1) + "s";
    }
  }

  function bulletList(title, items) {
    if (!items || !items.length) return "";
    return (
      '<p class="muted">' + esc(title) + "</p><ul>" +
      items.map((i) => "<li>" + esc(i) + "</li>").join("") +
      "</ul>"
    );
  }

  function renderResult(r) {
    const req = r.requirement;
    const cov = r.coverage;
    const cases = r.testCases || [];
    const score = Math.round((r.coverageScore || 0) * 100);

    const parts = [];
    parts.push(
      "<p><strong>" + esc(req.feature) + '</strong> · <span class="score">' +
        score + "% coverage</span> · " + cases.length + " test cases</p>"
    );
    parts.push(bulletList("Business Rules", req.business_rules));
    parts.push(bulletList("Risks", req.risks));
    parts.push(bulletList("Coverage gaps", cov.gaps));
    for (const c of cases) {
      parts.push(
        '<div class="case"><strong>' + esc(c.title) + "</strong><br>" +
          '<span class="tag">' + esc(c.type) + "</span>" +
          '<span class="tag">' + esc(c.priority) + "</span>" +
          (c.covers ? '<div class="muted">Covers: ' + esc(c.covers) + "</div>" : "") +
          "</div>"
      );
    }
    resultsEl.innerHTML = parts.join("");
  }

  // ── Intents (Webview → Host) ──────────────────────────────────────────────
  byId("analyze").addEventListener("click", () => {
    const markdown = requirementEl.value;
    if (!markdown.trim()) {
      statusEl.textContent = "Enter a requirement first.";
      return;
    }
    statusEl.textContent = "";
    resultsEl.innerHTML = '<p class="muted">Analyzing…</p>';
    vscode.postMessage({ type: "analyze", markdown });
  });
  byId("use-editor").addEventListener("click", () =>
    vscode.postMessage({ type: "useActiveEditor" })
  );
  byId("gen-tests").addEventListener("click", () =>
    vscode.postMessage({ type: "generate", markdown: requirementEl.value })
  );
  byId("export-md").addEventListener("click", () =>
    vscode.postMessage({ type: "export", format: "markdown" })
  );
  byId("export-json").addEventListener("click", () =>
    vscode.postMessage({ type: "export", format: "json" })
  );

  // ── State (Host → Webview) ────────────────────────────────────────────────
  window.addEventListener("message", (event) => {
    const msg = event.data;
    switch (msg.type) {
      case "steps":
        renderSteps(msg.steps);
        break;
      case "stepUpdate":
        updateStep(msg.step, msg.status, msg.durationMs);
        break;
      case "result":
        renderResult(msg.result);
        break;
      case "status":
        statusEl.textContent = msg.state === "idle" ? "" : msg.state;
        break;
      case "error":
        statusEl.textContent = "Error: " + msg.message;
        break;
      case "log":
        statusEl.textContent = msg.text;
        break;
      case "setMarkdown":
        requirementEl.value = msg.markdown;
        vscode.setState({ markdown: msg.markdown });
        break;
    }
  });

  // Tell the host we're ready to receive the initial state.
  vscode.postMessage({ type: "ready" });
})();
