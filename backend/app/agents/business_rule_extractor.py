"""BusinessRuleExtractor — extracts business rules from a Requirement via an LLM.

Returns a clean `list[str]`; does NOT mutate the Requirement (pure, composable).
The prompt -> extract-JSON -> validate -> retry machinery lives in `json_support`;
this agent only supplies the prompt, the schema, and its domain error.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.agents.json_support import DEFAULT_MAX_ATTEMPTS, complete_json
from app.models import Requirement
from app.providers import LLMProvider


class BusinessRuleExtractionError(RuntimeError):
    """Raised when the LLM output can't be parsed into rules after all retries."""


class _ExtractionResult(BaseModel):
    """The exact JSON shape we force the model's output into."""

    business_rules: list[str]


class BusinessRuleExtractor:
    """Extracts business rules from a Requirement using an injected LLM provider."""

    def __init__(
        self,
        provider: LLMProvider,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> None:
        self._provider = provider
        self._max_attempts = max_attempts

    def extract(self, requirement: Requirement) -> list[str]:
        """Return the business rules inferred from `requirement`."""
        result = complete_json(
            self._provider,
            self._build_prompt(requirement),
            _ExtractionResult,
            error_type=BusinessRuleExtractionError,
            max_attempts=self._max_attempts,
        )
        # Defensive cleanup: trim and drop blank rules the model may emit.
        return [rule.strip() for rule in result.business_rules if rule.strip()]

    def _build_prompt(self, requirement: Requirement) -> str:
        """Render the Requirement into instructions that demand JSON output."""
        criteria = (
            "\n".join(f"- {c}" for c in requirement.acceptance_criteria) or "(none)"
        )
        return (
            "You are a senior QA analyst. Extract the BUSINESS RULES implied by the "
            "requirement below. A business rule is a domain constraint the system "
            "must enforce (limits, eligibility, validation, state transitions). Infer "
            "the underlying rules; do not restate acceptance criteria verbatim.\n\n"
            f"Feature: {requirement.feature}\n"
            f"User story: {requirement.user_story or '(none)'}\n"
            f"Acceptance criteria:\n{criteria}\n\n"
            "Respond with ONLY a JSON object of this exact shape — no prose, no "
            'markdown:\n{"business_rules": ["rule 1", "rule 2"]}\n'
            'If there are none, return {"business_rules": []}.'
        )
