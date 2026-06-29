// Unit tests for the runtime shape guards — the backend "deserialize boundary".

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  isCoverageReport,
  isGenerationResult,
  isRequirement,
} from "../models/guards";

const validRequirement = {
  feature: "Login",
  user_story: "",
  acceptance_criteria: ["a"],
  business_rules: [],
  risks: [],
  notes: [],
};

test("isRequirement accepts a well-formed Requirement", () => {
  assert.equal(isRequirement(validRequirement), true);
});

test("isRequirement rejects drift (missing/renamed field, wrong type)", () => {
  assert.equal(isRequirement({ ...validRequirement, feature: 42 }), false);
  const { acceptance_criteria, ...withoutCriteria } = validRequirement;
  void acceptance_criteria;
  assert.equal(isRequirement(withoutCriteria), false);
  assert.equal(isRequirement(null), false);
});

test("isCoverageReport validates string arrays", () => {
  assert.equal(isCoverageReport({ covered: [], gaps: ["x"] }), true);
  assert.equal(isCoverageReport({ covered: [1], gaps: [] }), false);
});

test("isGenerationResult validates the nested shape", () => {
  const good = {
    requirement: validRequirement,
    coverage: { covered: [], gaps: [] },
    test_cases: [
      {
        title: "t",
        type: "positive",
        priority: "high",
        steps: ["s"],
        expected_result: "r",
        covers: "c",
      },
    ],
  };
  assert.equal(isGenerationResult(good), true);
  assert.equal(isGenerationResult({ ...good, test_cases: [{ title: "t" }] }), false);
});
