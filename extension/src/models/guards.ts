// Runtime shape guards for the backend DTOs.
//
// TypeScript interfaces vanish at runtime — a `... as GenerationResult` cast is
// a LIE the compiler can't check. If the backend changes a field name, the cast
// still "succeeds" and we render `undefined` somewhere deep in the UI. These
// guards validate the actual JSON at the trust boundary (BackendService), so a
// contract drift fails loudly with InvalidResponseError instead of silently.

import type {
  CoverageReport,
  GenerationResult,
  PlaywrightSpec,
  Requirement,
  TestCase,
} from "./requirement";

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null;
}

function isStringArray(v: unknown): v is string[] {
  return Array.isArray(v) && v.every((x) => typeof x === "string");
}

export function isRequirement(v: unknown): v is Requirement {
  return (
    isObject(v) &&
    typeof v.feature === "string" &&
    typeof v.user_story === "string" &&
    isStringArray(v.acceptance_criteria) &&
    isStringArray(v.business_rules) &&
    isStringArray(v.risks) &&
    isStringArray(v.notes)
  );
}

export function isCoverageReport(v: unknown): v is CoverageReport {
  return isObject(v) && isStringArray(v.covered) && isStringArray(v.gaps);
}

function isTestCase(v: unknown): v is TestCase {
  return (
    isObject(v) &&
    typeof v.title === "string" &&
    typeof v.type === "string" &&
    typeof v.priority === "string" &&
    isStringArray(v.steps) &&
    typeof v.expected_result === "string" &&
    typeof v.covers === "string"
  );
}

export function isPlaywrightSpec(v: unknown): v is PlaywrightSpec {
  return isObject(v) && typeof v.filename === "string" && typeof v.code === "string";
}

export function isGenerationResult(v: unknown): v is GenerationResult {
  return (
    isObject(v) &&
    isRequirement(v.requirement) &&
    isCoverageReport(v.coverage) &&
    Array.isArray(v.test_cases) &&
    v.test_cases.every(isTestCase)
  );
}
