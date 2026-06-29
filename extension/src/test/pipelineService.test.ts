// Unit tests for the pipeline orchestration. A fake BackendService lets us
// assert event ORDER and error-CONTINUATION without any network.

import assert from "node:assert/strict";
import { test } from "node:test";

import { PipelineService } from "../services/PipelineService";
import { scoreCoverage, type ProgressEvent } from "../models/pipeline";
import type { BackendService } from "../services/BackendService";
import type { Requirement } from "../models/requirement";

function requirement(extra: Partial<Requirement> = {}): Requirement {
  return {
    feature: "F",
    user_story: "",
    acceptance_criteria: ["a", "b"],
    business_rules: [],
    risks: [],
    notes: [],
    ...extra,
  };
}

function fakeBackend(overrides: Partial<BackendService> = {}): BackendService {
  const base: Partial<BackendService> = {
    parse: async () => requirement(),
    businessRules: async () => requirement({ business_rules: ["r1"] }),
    risks: async () => requirement({ risks: ["risk1"] }),
    coverage: async () => ({ covered: ["a"], gaps: ["b"] }),
    generate: async () => ({
      requirement: requirement({ business_rules: ["r1"], risks: ["risk1"] }),
      coverage: { covered: ["a"], gaps: ["b"] },
      test_cases: [
        {
          title: "t",
          type: "positive",
          priority: "high",
          steps: ["s"],
          expected_result: "r",
          covers: "a",
        },
      ],
    }),
  };
  return { ...base, ...overrides } as unknown as BackendService;
}

test("scoreCoverage: covered/(covered+gaps), 0 when empty", () => {
  assert.equal(scoreCoverage({ covered: ["a", "b"], gaps: ["c", "d"] }), 0.5);
  assert.equal(scoreCoverage({ covered: [], gaps: [] }), 0);
  assert.equal(scoreCoverage({ covered: ["a"], gaps: [] }), 1);
});

test("emits the 7 steps as done, in pipeline order, on success", async () => {
  const events: ProgressEvent[] = [];
  const pipeline = new PipelineService(fakeBackend());
  const result = await pipeline.analyze("md", (e) => events.push(e));

  const doneOrder = events.filter((e) => e.status === "done").map((e) => e.step);
  assert.deepEqual(doneOrder, [
    "parser",
    "rules",
    "risk",
    "rag",
    "coverage",
    "generate",
    "review",
  ]);
  assert.equal(result.testCases.length, 1);
  assert.equal(result.coverageScore, 0.5);
});

test("a failing INDEPENDENT step (risks) is marked error but the pipeline continues to generate", async () => {
  const events: ProgressEvent[] = [];
  const backend = fakeBackend({
    risks: async () => {
      throw new Error("risk analyzer boom");
    },
  });
  const pipeline = new PipelineService(backend);
  const result = await pipeline.analyze("md", (e) => events.push(e));

  assert.ok(events.some((e) => e.step === "risk" && e.status === "error"));
  // Reached and completed generate despite the earlier failure.
  assert.ok(events.some((e) => e.step === "generate" && e.status === "done"));
  // Result still produced; risks come from the authoritative /generate result.
  assert.equal(result.testCases.length, 1);
  assert.deepEqual(result.requirement.risks, ["risk1"]);
});

test("a failing REQUIRED step (generate) rejects, after emitting its error", async () => {
  const events: ProgressEvent[] = [];
  const backend = fakeBackend({
    generate: async () => {
      throw new Error("generation boom");
    },
  });
  const pipeline = new PipelineService(backend);

  await assert.rejects(() => pipeline.analyze("md", (e) => events.push(e)));
  assert.ok(events.some((e) => e.step === "generate" && e.status === "error"));
  assert.ok(events.some((e) => e.step === "parser" && e.status === "done"));
});
