// Transport for the backend's POST /requirements/generate endpoint.
//
// TEMPORARY (Milestone 1): this is the existing fetch client, relocated as-is
// so the current commands keep working during the scaffold migration — no
// behavior change. In Milestone 3 it is superseded by `api/ApiClient.ts`
// (timeout + retry + typed errors) and `services/BackendService.ts`, after
// which this file is deleted.

import type { GenerationResult } from "../models/requirement";

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
