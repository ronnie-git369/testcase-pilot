// Orchestrates the requirement -> test-cases pipeline as a sequence of real
// backend calls, emitting a ProgressEvent at each step transition so the UI can
// render the live "Agent Pipeline".
//
// Design choices (see the plan):
//  - "Sequential real calls": parse -> business-rules -> risks -> coverage ->
//    generate. Each response flips a step to done.
//  - Graceful degradation: an INDEPENDENT step that fails (rules/risk/coverage)
//    is marked error but the pipeline CONTINUES — a flaky middle step should not
//    sink the whole analysis. parser and generate are required.
//  - The /generate result is AUTHORITATIVE: steps 1-5 are a live preview, then
//    we override requirement/coverage with what /generate actually used, since
//    the LLM steps are non-deterministic and the independent calls may differ.
//
// Pure orchestration — no `vscode`. Progress is delivered via an injected
// callback, which keeps this unit-testable with a fake BackendService.

import type {
  CoverageReport,
  GenerationResult,
  Requirement,
} from "../models/requirement";
import {
  type AnalysisResult,
  type PipelineStep,
  type ProgressListener,
  type StepStatus,
  scoreCoverage,
} from "../models/pipeline";
import type { BackendService } from "./BackendService";

type EmitFn = (
  step: PipelineStep,
  status: StepStatus,
  durationMs?: number,
  message?: string
) => void;

function describe(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

export class PipelineService {
  constructor(private readonly backend: BackendService) {}

  async analyze(
    markdown: string,
    onProgress: ProgressListener = () => {}
  ): Promise<AnalysisResult> {
    const emit: EmitFn = (step, status, durationMs, message) =>
      onProgress({ step, status, durationMs, message });

    // 1. Parser — deterministic foundation. If it fails, we cannot continue.
    emit("parser", "running");
    let requirement: Requirement;
    try {
      const started = Date.now();
      requirement = await this.backend.parse(markdown);
      emit("parser", "done", Date.now() - started);
    } catch (err) {
      emit("parser", "error", undefined, describe(err));
      throw err;
    }

    // 2. Business rules — optional (degrade, don't abort).
    requirement = await this.optional(
      emit,
      "rules",
      () => this.backend.businessRules(markdown),
      requirement,
      (result, base) => ({ ...base, business_rules: result.business_rules })
    );

    // 3. Risks — optional.
    requirement = await this.optional(
      emit,
      "risk",
      () => this.backend.risks(markdown),
      requirement,
      (result, base) => ({ ...base, risks: result.risks })
    );

    // 4 + 5. RAG retrieval runs inside the coverage call (no own endpoint), so
    // both flip together. Coverage is optional too.
    emit("rag", "running");
    emit("coverage", "running");
    let coverage: CoverageReport = { covered: [], gaps: [] };
    try {
      const started = Date.now();
      coverage = await this.backend.coverage(markdown);
      const elapsed = Date.now() - started;
      emit("rag", "done", elapsed);
      emit("coverage", "done", elapsed);
    } catch (err) {
      emit("rag", "error", undefined, describe(err));
      emit("coverage", "error", undefined, describe(err));
    }

    // 6 + 7. Generate runs the full pipeline server-side; self-review is bundled
    // in its response, so "review" flips alongside "generate".
    emit("generate", "running");
    emit("review", "running");
    let result: GenerationResult;
    try {
      const started = Date.now();
      result = await this.backend.generate(markdown);
      const elapsed = Date.now() - started;
      emit("generate", "done", elapsed);
      emit("review", "done", elapsed);
    } catch (err) {
      emit("generate", "error", undefined, describe(err));
      emit("review", "error", undefined, describe(err));
      throw err;
    }

    // Override the preview with the authoritative /generate result.
    void requirement;
    void coverage;
    return {
      requirement: result.requirement,
      coverage: result.coverage,
      testCases: result.test_cases,
      coverageScore: scoreCoverage(result.coverage),
    };
  }

  /** Run an optional step: emit running -> done/error; on error keep `current`. */
  private async optional(
    emit: EmitFn,
    step: PipelineStep,
    call: () => Promise<Requirement>,
    current: Requirement,
    merge: (result: Requirement, base: Requirement) => Requirement
  ): Promise<Requirement> {
    emit(step, "running");
    try {
      const started = Date.now();
      const result = await call();
      emit(step, "done", Date.now() - started);
      return merge(result, current);
    } catch (err) {
      emit(step, "error", undefined, describe(err));
      return current;
    }
  }
}
