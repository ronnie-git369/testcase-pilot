// The typed contract between the extension HOST (Node) and the WEBVIEW (browser).
//
// Webviews talk to the host only via postMessage — an untyped `any` channel. We
// impose a discriminated union in BOTH directions so the compiler checks every
// message we send and every branch we handle. The webview stays a pure
// projection: it emits intents (WebviewToHost) and renders state (HostToWebview),
// never doing logic of its own.

import type {
  AnalysisResult,
  PipelineStep,
  StepStatus,
} from "./pipeline";

export type ExportFormat = "markdown" | "json";

export type BackendState =
  | "idle"
  | "connected"
  | "offline"
  | "analyzing"
  | "generating";

// ── Webview → Host (user intents) ──────────────────────────────────────────
export type WebviewToHost =
  | { type: "ready" }
  | { type: "analyze"; markdown: string }
  | { type: "generate"; markdown: string }
  | { type: "export"; format: ExportFormat }
  | { type: "useActiveEditor" };

// ── Host → Webview (state to render) ───────────────────────────────────────
export interface StepView {
  key: PipelineStep;
  label: string;
  status: StepStatus;
}

export type HostToWebview =
  | { type: "steps"; steps: StepView[] }
  | {
      type: "stepUpdate";
      step: PipelineStep;
      status: StepStatus;
      durationMs?: number;
      message?: string;
    }
  | { type: "result"; result: AnalysisResult }
  | { type: "status"; state: BackendState }
  | { type: "error"; message: string }
  | { type: "log"; text: string }
  | { type: "setMarkdown"; markdown: string };
