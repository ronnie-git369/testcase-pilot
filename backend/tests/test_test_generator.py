"""Unit tests for TestGeneratorAgent.

Offline and deterministic via a FakeProvider, despite the agent being
probabilistic in production.
"""

import pytest

from app.agents import TestGenerationError, TestGeneratorAgent
from app.models import Requirement, TestCase


class FakeProvider:
    def __init__(self, *responses: str) -> None:
        self._responses = list(responses)
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._responses.pop(0)


def make_requirement() -> Requirement:
    return Requirement(
        feature="Login",
        acceptance_criteria=["valid login works"],
        business_rules=["Lock account after 5 failed attempts"],
        risks=["Brute-force attacks"],
    )


VALID_RESPONSE = (
    '{"cases": [{"title": "Account locks after 5 failed logins", '
    '"type": "security", "priority": "high", '
    '"steps": ["Enter wrong password 5 times"], '
    '"expected_result": "Account is locked", "covers": "lockout gap"}]}'
)


def test_generate_returns_parsed_test_cases():
    cases = TestGeneratorAgent(FakeProvider(VALID_RESPONSE)).generate(
        make_requirement(), gaps=["account lockout not tested"]
    )

    assert len(cases) == 1
    case = cases[0]
    assert isinstance(case, TestCase)
    assert case.title == "Account locks after 5 failed logins"
    assert case.type == "security"
    assert case.priority == "high"
    assert case.steps == ["Enter wrong password 5 times"]
    assert case.covers == "lockout gap"  # traceability preserved


def test_prompt_includes_gaps_rules_and_risks():
    """The prompt carries gaps, business rules, and risks (the drivers).

    Prevents: generating blind to the coverage/risk signal that makes output
    high-value.
    """
    provider = FakeProvider('{"cases": []}')

    TestGeneratorAgent(provider).generate(
        make_requirement(), gaps=["account lockout not tested"]
    )

    sent = provider.prompts[0]
    assert "account lockout not tested" in sent  # gap
    assert "Lock account after 5 failed attempts" in sent  # business rule
    assert "Brute-force attacks" in sent  # risk


def test_incomplete_cases_are_dropped():
    """Cases missing a title or steps are filtered out.

    Prevents: emitting unusable, half-formed cases as if they were real.
    """
    response = (
        '{"cases": ['
        '{"title": "", "type": "positive", "priority": "low", '
        '"steps": ["do x"], "expected_result": "ok", "covers": "c"},'
        '{"title": "No steps", "type": "positive", "priority": "low", '
        '"steps": [], "expected_result": "ok", "covers": "c"},'
        '{"title": "Good one", "type": "positive", "priority": "low", '
        '"steps": ["do y"], "expected_result": "ok", "covers": "c"}'
        "]}"
    )

    cases = TestGeneratorAgent(FakeProvider(response)).generate(make_requirement())

    assert [c.title for c in cases] == ["Good one"]


def test_empty_suite_is_valid():
    cases = TestGeneratorAgent(FakeProvider('{"cases": []}')).generate(make_requirement())

    assert cases == []


def test_raises_on_unparseable_output():
    provider = FakeProvider("garbage", "still garbage")

    with pytest.raises(TestGenerationError):
        TestGeneratorAgent(provider).generate(make_requirement())
