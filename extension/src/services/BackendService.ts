// Typed facade over the backend endpoints.
//
// One method per endpoint. Each POSTs `{ markdown }` through the ApiClient, then
// runs a runtime shape guard so a drifted backend contract surfaces as a clear
// InvalidResponseError rather than an `undefined` deep in the UI. This is the
// DESERIALIZE BOUNDARY: above it, callers can trust the types.
//
// No `vscode`, no UI — it returns data or throws. (Logging/notifications happen
// in the command layer.)

import type { ApiClient } from "../api/ApiClient";
import { ENDPOINTS } from "../api/endpoints";
import { InvalidResponseError } from "../api/errors";
import {
  isCoverageReport,
  isGenerationResult,
  isPlaywrightSpec,
  isRequirement,
} from "../models/guards";
import type {
  CoverageReport,
  GenerationResult,
  PlaywrightSpec,
  Requirement,
  TestCase,
} from "../models/requirement";

export class BackendService {
  constructor(
    private readonly client: ApiClient,
    private readonly getProvider: () => string = () => "auto"
  ) {}

  /** Liveness probe. Returns false (not throws) on any failure — it's a yes/no. */
  async health(): Promise<boolean> {
    try {
      const res = await this.client.getJson<{ status?: string }>(ENDPOINTS.health);
      return res?.status === "healthy";
    } catch {
      return false;
    }
  }

  parse(markdown: string): Promise<Requirement> {
    return this.postGuarded(ENDPOINTS.parse, markdown, isRequirement);
  }

  businessRules(markdown: string): Promise<Requirement> {
    return this.postGuarded(ENDPOINTS.businessRules, markdown, isRequirement);
  }

  risks(markdown: string): Promise<Requirement> {
    return this.postGuarded(ENDPOINTS.risks, markdown, isRequirement);
  }

  coverage(markdown: string): Promise<CoverageReport> {
    return this.postGuarded(ENDPOINTS.coverage, markdown, isCoverageReport);
  }

  generate(markdown: string): Promise<GenerationResult> {
    return this.postGuarded(ENDPOINTS.generate, markdown, isGenerationResult);
  }

  /** Render a Playwright spec from already-generated test cases (no LLM). */
  async playwright(
    feature: string,
    testCases: TestCase[]
  ): Promise<PlaywrightSpec> {
    const data = await this.client.postJson<unknown>(ENDPOINTS.playwright, {
      feature,
      test_cases: testCases,
    });
    if (!isPlaywrightSpec(data)) {
      throw new InvalidResponseError(`unexpected shape from ${ENDPOINTS.playwright}`);
    }
    return data;
  }

  private async postGuarded<T>(
    path: string,
    markdown: string,
    guard: (value: unknown) => value is T
  ): Promise<T> {
    // Forward the provider hint when the user set one. The backend currently
    // selects its provider via env (LLM_PROVIDER) and ignores unknown body
    // fields, so this is a forward-compatible seam — honoring the per-request
    // provider is a future additive backend change.
    const provider = this.getProvider();
    const body =
      provider && provider !== "auto" ? { markdown, provider } : { markdown };

    const data = await this.client.postJson<unknown>(path, body);
    if (!guard(data)) {
      throw new InvalidResponseError(`unexpected shape from ${path}`);
    }
    return data;
  }
}
