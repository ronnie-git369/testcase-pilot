"""RiskAnalyzer — second LLM-backed agent.

Given a Requirement, asks an LLMProvider to identify the key testing RISKS and
returns them as a clean `list[str]`. Like BusinessRuleExtractor, it is pure
(returns data, does not mutate the Requirement) and validates the LLM's output.

NOTE (Rule of Three): this is the *second* agent that prompts for JSON, extracts
it, validates with Pydantic, and retries. The duplication with
business_rule_extractor.py is intentional for now — a *third* such agent will
justify extracting a shared base (e.g. a JsonAgent). Two is not yet evidence.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, ValidationError

from app.models import Requirement
from app.providers import LLMProvider

DEFAULT_MAX_ATTEMPTS = 2


class RiskAnalysisError(RuntimeError):
    """Raised when the LLM output can't be parsed into risks after all retries."""


class _RiskResult(BaseModel):
    """The exact JSON shape we force the model's output into."""

    risks: list[str]


class RiskAnalyzer:
    """Identifies testing risks for a Requirement using an injected LLM provider."""

    def __init__(
        self,
        provider: LLMProvider,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> None:
        self._provider = provider
        self._max_attempts = max_attempts

    def analyze(self, requirement: Requirement) -> list[str]:
        """Return the testing risks inferred from `requirement`.

        Makes up to `max_attempts` provider calls, parsing each response. Raises
        RiskAnalysisError if none parse.
        """
        prompt = self._build_prompt(requirement)
        last_error: Exception | None = None

        for _ in range(self._max_attempts):
            raw = self._provider.complete(prompt)
            try:
                return self._parse(raw)
            except (ValueError, ValidationError) as exc:
                last_error = exc

        raise RiskAnalysisError(
            "Could not parse risks from the LLM output."
        ) from last_error

    def _build_prompt(self, requirement: Requirement) -> str:
        """Render the Requirement into instructions that demand JSON output.

        Includes business_rules when present, so risks sharpen if this runs after
        rule extraction.
        """
        criteria = (
            "\n".join(f"- {c}" for c in requirement.acceptance_criteria) or "(none)"
        )
        rules = "\n".join(f"- {r}" for r in requirement.business_rules) or "(none)"
        return (
            "You are a senior QA risk analyst. Identify the key RISKS for testing the "
            "requirement below. A risk is something that could go wrong or is likely / "
            "costly to fail (security, data integrity, edge cases, performance, "
            "integration, compliance). Prioritize high-impact risks; be concise.\n\n"
            f"Feature: {requirement.feature}\n"
            f"User story: {requirement.user_story or '(none)'}\n"
            f"Acceptance criteria:\n{criteria}\n"
            f"Known business rules:\n{rules}\n\n"
            "Respond with ONLY a JSON object of this exact shape — no prose, no "
            'markdown:\n{"risks": ["risk 1", "risk 2"]}\n'
            'If there are none, return {"risks": []}.'
        )

    def _parse(self, raw: str) -> list[str]:
        """Turn a (possibly noisy) LLM response into a clean list of risks."""
        payload = self._extract_json_object(raw)
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM output was not valid JSON: {exc}") from exc

        result = _RiskResult.model_validate(data)
        return [risk.strip() for risk in result.risks if risk.strip()]

    @staticmethod
    def _extract_json_object(raw: str) -> str:
        """Slice out the JSON object from any prose/markdown wrapping."""
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("No JSON object found in the LLM output.")
        return raw[start : end + 1]
