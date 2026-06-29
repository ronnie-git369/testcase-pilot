# TestCasePilot — VS Code Extension

A thin client for the [TestCasePilot](../README.md) backend. Turn a requirement in
your editor into review-ready QA test cases without leaving VS Code.

## Usage

1. Start the backend (see the project README): `uvicorn app.main:app --reload`.
2. Open a Markdown requirement in VS Code (or select a portion of one).
3. Run the command **TestCasePilot: Generate Test Cases** (Command Palette: `Cmd/Ctrl+Shift+P`).
4. The generated cases — with business rules, risks, coverage gaps, and per-case
   traceability — open in a new Markdown tab.

If text is selected, only the selection is sent; otherwise the whole document is used.

## Configuration

| Setting | Default | Description |
| --- | --- | --- |
| `testcasePilot.apiUrl` | `http://127.0.0.1:8000` | Base URL of the backend API. |

## Develop

```bash
cd extension
npm install
npm run compile     # or: npm run watch
npm test            # unit tests for the Markdown renderer
```

Then press **F5** in VS Code to launch an Extension Development Host and try the command.

## Architecture

A thin client (ADR-0005): it only sends the requirement to the backend's
`POST /requirements/generate` and renders the response. All reasoning (parse → rules →
risk → retrieve → coverage → generate → self-review) happens server-side.

- `src/api.ts` — typed backend client (mirrors the backend models)
- `src/render.ts` — pure `GenerationResult → Markdown` formatter (unit-tested)
- `src/extension.ts` — command registration + VS Code wiring
