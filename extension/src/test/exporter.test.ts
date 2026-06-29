// Unit tests for the pure export builders.

import assert from "node:assert/strict";
import { test } from "node:test";

import { slugify, toJsonExport, toMarkdownExport } from "../services/exporter";
import type { AnalysisResult } from "../models/pipeline";

function sample(): AnalysisResult {
  return {
    requirement: {
      feature: "Password Reset",
      user_story: "",
      acceptance_criteria: ["link expires"],
      business_rules: ["one-time use"],
      risks: ["replay"],
      notes: [],
    },
    coverage: { covered: ["a"], gaps: ["b"] },
    testCases: [
      {
        title: "expiry",
        type: "negative",
        priority: "high",
        steps: ["wait"],
        expected_result: "rejected",
        covers: "link expires",
      },
    ],
    coverageScore: 0.5,
  };
}

test("slugify produces a safe, stable filename stem", () => {
  assert.equal(slugify("Password Reset!"), "password-reset");
  assert.equal(slugify("  Multi   Word  "), "multi-word");
  assert.equal(slugify("***"), "requirement");
});

test("markdown export names the file from the feature and renders a report", () => {
  const payload = toMarkdownExport(sample());
  assert.equal(payload.fileName, "password-reset.md");
  assert.match(payload.content, /^# Test Cases — Password Reset/m);
});

test("json export is valid JSON carrying the score and cases", () => {
  const payload = toJsonExport(sample());
  assert.equal(payload.fileName, "password-reset.json");
  const parsed = JSON.parse(payload.content);
  assert.equal(parsed.feature, "Password Reset");
  assert.equal(parsed.coverageScore, 0.5);
  assert.equal(parsed.testCases.length, 1);
});
