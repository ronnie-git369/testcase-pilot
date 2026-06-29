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
  isRequirement,
} from "../models/guards";
import type {
  CoverageReport,
  GenerationResult,
  Requirement,
} from "../models/requirement";

export class BackendService {
  constructor(private readonly client: ApiClient) {}

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

  private async postGuarded<T>(
    path: string,
    markdown: string,
    guard: (value: unknown) => value is T
  ): Promise<T> {
    const data = await this.client.postJson<unknown>(path, { markdown });
    if (!guard(data)) {
      throw new InvalidResponseError(`unexpected shape from ${path}`);
    }
    return data;
  }
}
