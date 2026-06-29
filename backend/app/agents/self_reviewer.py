"""SelfReviewer — critiques and revises generated test cases (the self-review step).

Takes the draft TestCases plus the Requirement, asks the LLM to critique them
(duplicates, missing negative/edge cases, vague steps, weak assertions) and return
an IMPROVED set. Pure; reuses the shared `complete_json` helper and the `TestSuite`
schema — the fifth agent on that helper, with no new parsing code.
"""

from __future__ import annotations

import json

from app.agents.json_support import DEFAULT_MAX_ATTEMPTS, complete_json
from app.models import Requirement, TestCase, TestSuite
from app.providers import LLMProvider


class SelfReviewError(RuntimeError):
    """Raised when the LLM review output can't be parsed after retries."""


class SelfReviewer:
    """Reviews and revises a draft set of test cases using an injected provider."""

    def __init__(
        self,
        provider: LLMProvider,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> None:
        self._provider = provider
        self._max_attempts = max_attempts

    def review(
        self,
        requirement: Requirement,
        cases: list[TestCase],
    ) -> list[TestCase]:
        """Return an improved set of test cases. No cases in -> no LLM call."""
        if not cases:
            return []

        suite = complete_json(
            self._provider,
            self._build_prompt(requirement, cases),
            TestSuite,
            error_type=SelfReviewError,
            max_attempts=self._max_attempts,
        )
        return [
            case
            for case in suite.cases
            if case.title.strip() and any(s.strip() for s in case.steps)
        ]

    def _build_prompt(self, requirement: Requirement, cases: list[TestCase]) -> str:
        def bullets(items: list[str]) -> str:
            return "\n".join(f"- {i}" for i in items) or "(none)"

        draft = json.dumps(
            {"cases": [case.model_dump() for case in cases]}, indent=2
        )
        return (
            "You are a senior QA reviewer. Critique the DRAFT test cases below against "
            "the requirement, then return an IMPROVED set. Look for: duplicate or "
            "overlapping cases, missing negative/edge cases, vague steps, and weak or "
            "non-specific expected results. Merge duplicates, tighten steps and "
            "assertions, and add missing high-value cases. Keep `covers` accurate.\n\n"
            f"Feature: {requirement.feature}\n"
            f"Acceptance criteria:\n{bullets(requirement.acceptance_criteria)}\n"
            f"Business rules:\n{bullets(requirement.business_rules)}\n"
            f"Risks:\n{bullets(requirement.risks)}\n\n"
            f"DRAFT cases:\n{draft}\n\n"
            "Respond with ONLY a JSON object of this exact shape — no prose, no "
            "markdown:\n"
            '{"cases": [{"title": "...", "type": "...", "priority": "...", '
            '"steps": ["..."], "expected_result": "...", "covers": "..."}]}'
        )
