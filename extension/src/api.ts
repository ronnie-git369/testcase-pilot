// Typed client for the TestCasePilot backend. Mirrors the backend Pydantic models.

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

/**
 * POST a Markdown requirement to the backend's /requirements/generate endpoint
 * and return the full pipeline result. Throws a friendly Error on failure.
 */
export async function generateTestCases(
  apiUrl: string,
  markdown: string
): Promise<GenerationResult> {
  const url = `${apiUrl.replace(/\/+$/, "")}/requirements/generate`;

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ markdown }),
  }).catch(() => {
    throw new Error(`could not reach the backend at ${apiUrl}. Is it running?`);
  });

  if (!response.ok) {
    throw new Error(
      `backend returned ${response.status} ${response.statusText}`
    );
  }

  return (await response.json()) as GenerationResult;
}
