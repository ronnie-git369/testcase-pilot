"""Unit tests for RiskAnalyzer.

Mirrors the BusinessRuleExtractor tests — same offline, deterministic approach
via a FakeProvider at the LLMProvider port.
"""

import pytest

from app.agents import RiskAnalysisError, RiskAnalyzer
from app.models import Requirement


class FakeProvider:
    """Returns queued responses; records prompts. Structurally an LLMProvider."""

    def __init__(self, *responses: str) -> None:
        self._responses = list(responses)
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._responses.pop(0)


def make_requirement() -> Requirement:
    return Requirement(
        feature="Login",
        user_story="As a user I want to log in",
        acceptance_criteria=["account locks after 5 failed attempts"],
        business_rules=["Accounts lock after 5 consecutive failed attempts"],
    )


def test_analyze_returns_risks_from_valid_json():
    provider = FakeProvider(
        '{"risks": ["Brute-force attacks", "Lockout denial-of-service"]}'
    )

    risks = RiskAnalyzer(provider).analyze(make_requirement())

    assert risks == ["Brute-force attacks", "Lockout denial-of-service"]


def test_analyze_handles_json_wrapped_in_prose_and_fences():
    provider = FakeProvider('Here:\n```json\n{"risks": ["Session fixation"]}\n```')

    assert RiskAnalyzer(provider).analyze(make_requirement()) == ["Session fixation"]


def test_analyze_strips_whitespace_and_drops_empty_risks():
    provider = FakeProvider('{"risks": ["  timing attack  ", "", "  "]}')

    assert RiskAnalyzer(provider).analyze(make_requirement()) == ["timing attack"]


def test_analyze_returns_empty_list_when_there_are_no_risks():
    assert RiskAnalyzer(FakeProvider('{"risks": []}')).analyze(make_requirement()) == []


def test_analyze_retries_once_then_succeeds():
    provider = FakeProvider("not json", '{"risks": ["Recovered risk"]}')

    risks = RiskAnalyzer(provider).analyze(make_requirement())

    assert risks == ["Recovered risk"]
    assert len(provider.prompts) == 2


def test_analyze_raises_after_repeated_invalid_output():
    provider = FakeProvider("garbage", "still garbage")

    with pytest.raises(RiskAnalysisError):
        RiskAnalyzer(provider).analyze(make_requirement())


def test_prompt_includes_business_rules_for_context():
    """Risks build on rules: the prompt must carry known business rules.

    Prevents: the analyzer ignoring context already gathered upstream.
    """
    provider = FakeProvider('{"risks": []}')

    RiskAnalyzer(provider).analyze(make_requirement())

    sent = provider.prompts[0]
    assert "Login" in sent
    assert "Accounts lock after 5 consecutive failed attempts" in sent
