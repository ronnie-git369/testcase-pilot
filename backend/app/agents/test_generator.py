"""TestGeneratorAgent — generates review-ready test cases from a Requirement.

The payoff agent: it consumes everything upstream produced (rules, risks, and the
coverage gaps from #8) and emits a focused, traceable set of TestCases. Prioritizes
gaps and risks — depth over volume — and tags each case with what it `covers`.

Pure (returns cases, mutates nothing) and the fourth agent built on the shared
`complete_json` helper — no new parsing code.
"""

from __future__ import annotations

from app.agents.json_support import DEFAULT_MAX_ATTEMPTS, complete_json
from app.models import Requirement, TestCase, TestSuite
from app.providers import LLMProvider


class TestGenerationError(RuntimeError):
    """Raised when the LLM output can't be parsed into test cases after retries."""


class TestGeneratorAgent:
    """Generates manual test cases for a Requirement using an injected provider."""

    def __init__(
        self,
        provider: LLMProvider,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> None:
        self._provider = provider
        self._max_attempts = max_attempts

    def generate(
        self,
        requirement: Requirement,
        gaps: list[str] | None = None,
    ) -> list[TestCase]:
        """Return generated test cases, prioritizing `gaps` and the requirement's risks."""
        suite = complete_json(
            self._provider,
            self._build_prompt(requirement, gaps or []),
            TestSuite,
            error_type=TestGenerationError,
            max_attempts=self._max_attempts,
        )
        # Drop incomplete cases the model may emit (no title or no steps).
        return [
            case
            for case in suite.cases
            if case.title.strip() and any(s.strip() for s in case.steps)
        ]

    def _build_prompt(self, requirement: Requirement, gaps: list[str]) -> str:
        def bullets(items: list[str]) -> str:
            return "\n".join(f"- {i}" for i in items) or "(none)"

        return (
            "You are a senior QA engineer writing enterprise-quality MANUAL test cases. "
            "Favor depth over volume: a few high-signal cases beat many shallow ones. "
            "PRIORITIZE the coverage gaps and risks below; do not re-test what is "
            "already covered. Set `covers` on every case to the specific rule, risk, or "
            "gap it addresses.\n\n"
            f"Feature: {requirement.feature}\n"
            f"User story: {requirement.user_story or '(none)'}\n"
            f"Acceptance criteria:\n{bullets(requirement.acceptance_criteria)}\n"
            f"Business rules:\n{bullets(requirement.business_rules)}\n"
            f"Risks:\n{bullets(requirement.risks)}\n"
            f"Coverage gaps to target first:\n{bullets(gaps)}\n\n"
            "Respond with ONLY a JSON object of this exact shape — no prose, no "
            "markdown:\n"
            '{"cases": [{"title": "...", "type": "positive|negative|edge|security", '
            '"priority": "high|medium|low", "steps": ["..."], '
            '"expected_result": "...", "covers": "the rule/risk/gap addressed"}]}\n'
            'If nothing is worth generating, return {"cases": []}.'
        )
