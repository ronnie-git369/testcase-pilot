// Backend endpoint paths + URL construction.
//
// Centralizing paths keeps them in lockstep with the FastAPI routes and out of
// the call sites. `buildUrl` normalizes the base (trailing slashes) so callers
// never produce `http://host//requirements/parse`.

export const ENDPOINTS = {
  parse: "/requirements/parse",
  businessRules: "/requirements/business-rules",
  risks: "/requirements/risks",
  coverage: "/requirements/coverage",
  generate: "/requirements/generate",
  retrievalSearch: "/retrieval/search",
  playwright: "/tests/playwright",
  health: "/health",
} as const;

export function buildUrl(baseUrl: string, path: string): string {
  return `${baseUrl.replace(/\/+$/, "")}${path}`;
}
