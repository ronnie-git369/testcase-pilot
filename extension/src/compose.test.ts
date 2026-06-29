// Unit tests for the pure Markdown composer, using Node's built-in test runner.
// Run after compiling: `npm test` (node --test out/).

import assert from "node:assert/strict";
import { test } from "node:test";

import { buildRequirementMarkdown } from "./compose";

test("emits the feature as an H1 heading", () => {
  const md = buildRequirementMarkdown({
    feature: "Password Reset",
    userStory: "",
    acceptanceCriteria: [],
  });
  assert.match(md, /^# Password Reset/m);
});

test("emits a User Story section the parser recognizes", () => {
  const md = buildRequirementMarkdown({
    feature: "Login",
    userStory: "As a user I want to log in",
    acceptanceCriteria: [],
  });
  assert.match(md, /## User Story\nAs a user I want to log in/);
});

test("emits acceptance criteria as bullets, trimming and dropping blanks", () => {
  const md = buildRequirementMarkdown({
    feature: "Login",
    userStory: "",
    acceptanceCriteria: ["  valid login works  ", "", "   ", "errors show a message"],
  });
  assert.match(md, /## Acceptance Criteria\n- valid login works\n- errors show a message/);
  assert.doesNotMatch(md, /- *\n/); // no empty bullets
});

test("omits optional sections when their inputs are empty", () => {
  const md = buildRequirementMarkdown({
    feature: "Bare",
    userStory: "   ",
    acceptanceCriteria: [],
  });
  assert.doesNotMatch(md, /User Story/);
  assert.doesNotMatch(md, /Acceptance Criteria/);
  assert.equal(md.trim(), "# Bare");
});
