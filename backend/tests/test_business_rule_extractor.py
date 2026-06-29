"""Unit tests for BusinessRuleExtractor.

The agent itself is probabilistic in production, but its *logic* (prompt
building, JSON extraction, validation, retry) is fully deterministic. We test it
against a FakeProvider with canned responses — no network, no API key, no cost.
This is the payoff of depending on the LLMProvider port instead of a vendor SDK.
"""

import pytest

from app.agents import BusinessRuleExtractionError, BusinessRuleExtractor
from app.models import Requirement


class FakeProvider:
    """An LLMProvider that returns queued responses and records prompts sent.

    Structurally satisfies the LLMProvider Protocol (it has `complete`) without
    importing or subclassing it.
    """

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
    )


def test_extract_returns_rules_from_valid_json():
    """A clean JSON object yields the list of rules verbatim."""
    provider = FakeProvider(
        '{"business_rules": ["Lock account after 5 failures", "Passwords are case-sensitive"]}'
    )

    rules = BusinessRuleExtractor(provider).extract(make_requirement())

    assert rules == ["Lock account after 5 failures", "Passwords are case-sensitive"]


def test_extract_handles_json_wrapped_in_prose_and_fences():
    """Real models add chatter / ```json fences; we still recover the object.

    Prevents: a perfectly good answer being thrown away over cosmetic wrapping.
    """
    provider = FakeProvider(
        'Sure! Here you go:\n```json\n{"business_rules": ["Only verified emails may log in"]}\n```'
    )

    rules = BusinessRuleExtractor(provider).extract(make_requirement())

    assert rules == ["Only verified emails may log in"]


def test_extract_strips_whitespace_and_drops_empty_rules():
    """Blank/whitespace rules the model emits are cleaned out."""
    provider = FakeProvider('{"business_rules": ["  trimmed  ", "", "   "]}')

    assert BusinessRuleExtractor(provider).extract(make_requirement()) == ["trimmed"]


def test_extract_returns_empty_list_when_there_are_no_rules():
    """An empty rules array is a valid result, not an error."""
    provider = FakeProvider('{"business_rules": []}')

    assert BusinessRuleExtractor(provider).extract(make_requirement()) == []


def test_extract_retries_once_then_succeeds():
    """A first unparseable response is retried; the second succeeds.

    Prevents: a single transient bad generation failing the whole request.
    """
    provider = FakeProvider("not json at all", '{"business_rules": ["Recovered rule"]}')

    rules = BusinessRuleExtractor(provider).extract(make_requirement())

    assert rules == ["Recovered rule"]
    assert len(provider.prompts) == 2  # it actually retried


def test_extract_raises_after_repeated_invalid_output():
    """If every attempt is garbage, raise a clear domain error.

    Prevents: silently returning [] when the LLM is actually broken — that would
    look like 'no rules' instead of 'extraction failed'.
    """
    provider = FakeProvider("garbage", "still garbage")

    with pytest.raises(BusinessRuleExtractionError):
        BusinessRuleExtractor(provider).extract(make_requirement())


def test_prompt_includes_the_requirement_details():
    """The prompt is built from the Requirement's fields.

    Prevents: silently sending an empty/decoupled prompt that ignores the input.
    """
    provider = FakeProvider('{"business_rules": []}')

    BusinessRuleExtractor(provider).extract(make_requirement())

    sent = provider.prompts[0]
    assert "Login" in sent
    assert "account locks after 5 failed attempts" in sent
