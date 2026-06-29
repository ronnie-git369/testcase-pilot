"""BusinessRuleExtractor — the first LLM-backed agent.

Given a Requirement, it asks an LLMProvider to infer the domain BUSINESS RULES
and returns them as a clean `list[str]`. It does NOT mutate the Requirement —
the caller (later, the orchestrator) merges the result. Single responsibility,
pure, and testable offline via a fake provider.

Because LLM output is non-deterministic and unstructured, this agent owns the
job of turning messy text into a validated structure: it prompts for JSON,
extracts and parses it, validates the shape with Pydantic, and retries once
before giving up.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, ValidationError

from app.models import Requirement
from app.providers import LLMProvider

DEFAULT_MAX_ATTEMPTS = 2


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
        """Return the business rules inferred from `requirement`.

        Makes up to `max_attempts` calls to the provider, parsing each response.
        Raises BusinessRuleExtractionError if none parse.
        """
        prompt = self._build_prompt(requirement)
        last_error: Exception | None = None

        for _ in range(self._max_attempts):
            raw = self._provider.complete(prompt)
            try:
                return self._parse(raw)
            except (ValueError, ValidationError) as exc:
                last_error = exc  # keep trying

        raise BusinessRuleExtractionError(
            "Could not parse business rules from the LLM output."
        ) from last_error

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

    def _parse(self, raw: str) -> list[str]:
        """Turn a (possibly noisy) LLM response into a clean list of rules."""
        payload = self._extract_json_object(raw)
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM output was not valid JSON: {exc}") from exc

        result = _ExtractionResult.model_validate(data)
        # Defensive cleanup: trim and drop blank rules the model may emit.
        return [rule.strip() for rule in result.business_rules if rule.strip()]

    @staticmethod
    def _extract_json_object(raw: str) -> str:
        """Slice out the JSON object from prose/markdown the model may wrap it in.

        Models often add 'Sure! ...' or ```json fences. Taking the span from the
        first '{' to the last '}' tolerates both without special-casing fences.
        """
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("No JSON object found in the LLM output.")
        return raw[start : end + 1]
