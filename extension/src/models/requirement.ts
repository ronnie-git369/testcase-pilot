// Shared DTO interfaces that mirror the backend's Pydantic models.
//
// Pure types — zero runtime code, no `vscode` or `node` imports — so every
// layer (api, services, views, tests) can depend on them without coupling to
// the editor or the network. This is the contract between the thin client and
// the FastAPI backend; if the backend changes a field, it changes here once.

export interface Requirement {
  feature: string;
  user_story: string;
  acceptance_criteria: string[];
  business_rules: string[];
  risks: string[];
  notes: string[];
}

export interface CoverageReport {
  covered: string[];
  gaps: string[];
}

export interface TestCase {
  title: string;
  type: string;
  priority: string;
  steps: string[];
  expected_result: string;
  covers: string;
}

export interface GenerationResult {
  requirement: Requirement;
  coverage: CoverageReport;
  test_cases: TestCase[];
}

export interface PlaywrightSpec {
  filename: string;
  code: string;
}
