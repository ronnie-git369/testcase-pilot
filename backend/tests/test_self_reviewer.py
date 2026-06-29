"""Unit tests for SelfReviewer (offline via FakeProvider)."""

import pytest

from app.agents import SelfReviewError, SelfReviewer
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


def draft_cases() -> list[TestCase]:
    return [
        TestCase(
            title="Login works",
            type="positive",
            priority="high",
            steps=["enter creds"],
            expected_result="logged in",
            covers="valid login works",
        )
    ]


REVISED = (
    '{"cases": [{"title": "Login works (revised)", "type": "positive", '
    '"priority": "high", "steps": ["enter valid creds", "submit"], '
    '"expected_result": "dashboard is shown", "covers": "valid login works"}]}'
)


def test_review_returns_revised_cases():
    cases = SelfReviewer(FakeProvider(REVISED)).review(make_requirement(), draft_cases())

    assert len(cases) == 1
    assert cases[0].title == "Login works (revised)"
    assert cases[0].steps == ["enter valid creds", "submit"]


def test_review_skips_llm_when_there_are_no_cases():
    """No drafts -> return [] without calling the provider (don't waste a call)."""
    provider = FakeProvider()  # no queued responses; calling it would IndexError

    result = SelfReviewer(provider).review(make_requirement(), [])

    assert result == []
    assert provider.prompts == []  # the LLM was never called


def test_prompt_includes_the_draft_cases_and_requirement_context():
    """The draft cases and risks reach the model so it can critique them.

    Prevents: 'reviewing' without actually seeing the drafts or the requirement.
    """
    provider = FakeProvider('{"cases": []}')

    SelfReviewer(provider).review(make_requirement(), draft_cases())

    sent = provider.prompts[0]
    assert "Login works" in sent  # the draft case title
    assert "Brute-force attacks" in sent  # a risk from the requirement


def test_incomplete_revised_cases_are_dropped():
    response = (
        '{"cases": ['
        '{"title": "", "type": "positive", "priority": "low", '
        '"steps": ["x"], "expected_result": "ok", "covers": "c"},'
        '{"title": "Kept", "type": "positive", "priority": "low", '
        '"steps": ["y"], "expected_result": "ok", "covers": "c"}'
        "]}"
    )

    cases = SelfReviewer(FakeProvider(response)).review(make_requirement(), draft_cases())

    assert [c.title for c in cases] == ["Kept"]


def test_raises_on_unparseable_output():
    provider = FakeProvider("garbage", "still garbage")

    with pytest.raises(SelfReviewError):
        SelfReviewer(provider).review(make_requirement(), draft_cases())
