// Pure builders for export artifacts: turn an AnalysisResult into the bytes we
// write to disk (Markdown report or structured JSON) plus a sensible filename.
//
// No `vscode`, no filesystem — just data in, payload out — so it's unit-tested
// in plain Node. The actual writing (dialogs, fs, confirmation) is WorkspaceService.

import type { AnalysisResult } from "../models/pipeline";
import type { GenerationResult } from "../models/requirement";
import { renderReport } from "./render";

export interface ExportPayload {
  fileName: string;
  content: string;
}

/** "Password Reset!" -> "password-reset" (safe, stable filename stem). */
export function slugify(feature: string): string {
  return (
    feature
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "requirement"
  );
}

export function toMarkdownExport(result: AnalysisResult): ExportPayload {
  const generation: GenerationResult = {
    requirement: result.requirement,
    coverage: result.coverage,
    test_cases: result.testCases,
  };
  return {
    fileName: `${slugify(result.requirement.feature)}.md`,
    content: renderReport(generation),
  };
}

export function toJsonExport(result: AnalysisResult): ExportPayload {
  const payload = {
    feature: result.requirement.feature,
    requirement: result.requirement,
    coverage: result.coverage,
    coverageScore: result.coverageScore,
    testCases: result.testCases,
  };
  return {
    fileName: `${slugify(result.requirement.feature)}.json`,
    content: JSON.stringify(payload, null, 2) + "\n",
  };
}
