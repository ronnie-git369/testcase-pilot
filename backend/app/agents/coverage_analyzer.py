"""CoverageAnalyzer — the first dual-port agent.

Depends on BOTH a TestCaseRetriever (to find existing tests) and an LLMProvider
(to reason about what's missing). Given a Requirement, it returns a CoverageReport
classifying each acceptance criterion / business rule as already covered or a gap.

This closes the RAG loop: retrieve (deterministic) then reason (probabilistic).
Both dependencies are injected, so tests run offline with a FakeRetriever +
FakeProvider.
"""

from __future__ import annotations

from app.agents.json_support import DEFAULT_MAX_ATTEMPTS, complete_json
from app.models import CoverageReport, Requirement
from app.providers import LLMProvider
from app.retrieval import TestCaseRetriever

DEFAULT_K = 3


class CoverageAnalysisError(RuntimeError):
    """Raised when the LLM output can't be parsed into a CoverageReport."""


class CoverageAnalyzer:
    """Finds testing coverage gaps by comparing a Requirement to existing tests."""

    def __init__(
        self,
        provider: LLMProvider,
        retriever: TestCaseRetriever,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> None:
        self._provider = provider
        self._retriever = retriever
        self._max_attempts = max_attempts

    def analyze(self, requirement: Requirement, k: int = DEFAULT_K) -> CoverageReport:
        """Return a CoverageReport for `requirement` against the indexed tests."""
        existing = self._retrieve_existing(requirement, k)
        prompt = self._build_prompt(requirement, existing)
        report = complete_json(
            self._provider,
            prompt,
            CoverageReport,
            error_type=CoverageAnalysisError,
            max_attempts=self._max_attempts,
        )
        # Defensive cleanup of blank entries the model may emit.
        return CoverageReport(
            covered=[c.strip() for c in report.covered if c.strip()],
            gaps=[g.strip() for g in report.gaps if g.strip()],
        )

    def _retrieve_existing(self, requirement: Requirement, k: int) -> list:
        """Search per criterion and business rule; dedupe results by id.

        Searching each facet separately surfaces tests relevant to *that* facet;
        deduping by id keeps each existing test in the prompt exactly once.
        """
        queries = list(requirement.acceptance_criteria) + list(
            requirement.business_rules
        )
        if not queries:  # nothing structured yet — fall back to the feature name
            queries = [requirement.feature]

        seen: dict[str, object] = {}
        for query in queries:
            for result in self._retriever.search(query, k=k):
                seen.setdefault(result.id, result)
        return list(seen.values())

    def _build_prompt(self, requirement: Requirement, existing: list) -> str:
        criteria = (
            "\n".join(f"- {c}" for c in requirement.acceptance_criteria) or "(none)"
        )
        rules = "\n".join(f"- {r}" for r in requirement.business_rules) or "(none)"
        existing_text = (
            "\n".join(f"- {e.text}" for e in existing) or "(none found)"
        )
        return (
            "You are a senior QA coverage analyst. Compare the requirement against the "
            "EXISTING test cases below and decide what is already covered and what is "
            "missing.\n\n"
            f"Feature: {requirement.feature}\n"
            f"User story: {requirement.user_story or '(none)'}\n"
            f"Acceptance criteria:\n{criteria}\n"
            f"Business rules:\n{rules}\n\n"
            f"Existing test cases already in our suite:\n{existing_text}\n\n"
            "Classify each acceptance criterion and business rule: is it COVERED by an "
            "existing test, or is it a GAP (nothing addresses it)? Describe gaps as "
            "specific, testable aspects.\n"
            "Respond with ONLY a JSON object of this exact shape — no prose, no "
            'markdown:\n{"covered": ["aspect already tested"], "gaps": ["aspect not '
            'yet tested"]}\nUse empty arrays where appropriate.'
        )
