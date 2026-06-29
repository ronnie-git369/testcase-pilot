// Unit tests for the pure Markdown renderer, using Node's built-in test runner.
// Run after compiling: `npm test` (node --test out/).

import assert from "node:assert/strict";
import { test } from "node:test";

import { renderReport } from "./render";
import type { GenerationResult } from "./api";

function sampleResult(): GenerationResult {
  return {
    requirement: {
      feature: "Login",
      user_story: "As a user I want to log in",
      acceptance_criteria: ["valid login works"],
      business_rules: ["Lock account after 5 failed attempts"],
      risks: ["Brute-force attacks"],
      notes: [],
    },
    coverage: { covered: ["valid login is tested"], gaps: ["account lockout not tested"] },
    test_cases: [
      {
        title: "Account locks after 5 failed logins",
        type: "security",
        priority: "high",
        steps: ["Submit wrong password 5 times", "Attempt a 6th login"],
        expected_result: "6th attempt is blocked",
        covers: "account lockout not tested",
      },
    ],
  };
}

test("renders the feature heading and case count", () => {
  const md = renderReport(sampleResult());
  assert.match(md, /^# Test Cases — Login/m);
  assert.match(md, /## Test Cases \(1\)/);
});

test("includes rules, risks, coverage gaps, and traceability", () => {
  const md = renderReport(sampleResult());
  assert.match(md, /Lock account after 5 failed attempts/);
  assert.match(md, /Brute-force attacks/);
  assert.match(md, /account lockout not tested/);
  assert.match(md, /_Covers:_ account lockout not tested/);
});

test("numbers the steps", () => {
  const md = renderReport(sampleResult());
  assert.match(md, /1\. Submit wrong password 5 times/);
  assert.match(md, /2\. Attempt a 6th login/);
});

test("handles an empty result gracefully", () => {
  const empty: GenerationResult = {
    requirement: {
      feature: "Untitled",
      user_story: "",
      acceptance_criteria: [],
      business_rules: [],
      risks: [],
      notes: ["No feature heading found; defaulted to 'Untitled'."],
    },
    coverage: { covered: [], gaps: [] },
    test_cases: [],
  };
  const md = renderReport(empty);
  assert.match(md, /_No test cases were generated._/);
  assert.match(md, /_\(none\)_/);
  assert.match(md, /## Notes/);
});
