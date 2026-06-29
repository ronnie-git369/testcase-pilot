"""RiskAnalyzer — identifies testing risks for a Requirement via an LLM.

Returns a clean `list[str]`; pure (no Requirement mutation). Shares the
prompt -> extract-JSON -> validate -> retry machinery in `json_support`.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.agents.json_support import DEFAULT_MAX_ATTEMPTS, complete_json
from app.models import Requirement
from app.providers import LLMProvider


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
        """Return the testing risks inferred from `requirement`."""
        result = complete_json(
            self._provider,
            self._build_prompt(requirement),
            _RiskResult,
            error_type=RiskAnalysisError,
            max_attempts=self._max_attempts,
        )
        return [risk.strip() for risk in result.risks if risk.strip()]

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
