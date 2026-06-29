// The pipeline's vocabulary: the seven steps the UI shows, their statuses, the
// progress events the service emits, and the assembled result.
//
// Mapping to the backend (see the plan): only 5 of the 7 steps are real HTTP
// calls. "RAG Retrieval" runs INSIDE the coverage call (no own endpoint), and
// "Self Review" is bundled inside /generate — so those two flip alongside their
// host call rather than from a dedicated request.

import type { CoverageReport, Requirement, TestCase } from "./requirement";

export type PipelineStep =
  | "parser"
  | "rules"
  | "risk"
  | "rag"
  | "coverage"
  | "generate"
  | "review";

export type StepStatus = "pending" | "running" | "done" | "error";

export interface PipelineStepInfo {
  key: PipelineStep;
  label: string;
}

// Ordered for display in the sidebar's "Agent Pipeline" list.
export const PIPELINE_STEPS: readonly PipelineStepInfo[] = [
  { key: "parser", label: "Requirement Parser" },
  { key: "rules", label: "Business Rule Extractor" },
  { key: "risk", label: "Risk Analyzer" },
  { key: "rag", label: "RAG Retrieval" },
  { key: "coverage", label: "Coverage Analysis" },
  { key: "generate", label: "Test Generation" },
  { key: "review", label: "Self Review" },
] as const;

export interface ProgressEvent {
  step: PipelineStep;
  status: StepStatus;
  durationMs?: number;
  /** Present when status === "error". */
  message?: string;
}

export type ProgressListener = (event: ProgressEvent) => void;

export interface AnalysisResult {
  requirement: Requirement;
  coverage: CoverageReport;
  testCases: TestCase[];
  /** Estimated coverage, 0..1: covered / (covered + gaps). */
  coverageScore: number;
}

export function scoreCoverage(coverage: CoverageReport): number {
  const total = coverage.covered.length + coverage.gaps.length;
  return total === 0 ? 0 : coverage.covered.length / total;
}
