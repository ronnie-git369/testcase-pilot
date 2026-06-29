"""Unit tests for CoverageAnalyzer (the dual-port agent).

Both dependencies are faked: a FakeProvider (canned LLM output) and a
StubRetriever (canned existing tests, records queries). Fully offline and
deterministic, despite the agent being probabilistic in production.
"""

import pytest

from app.agents import CoverageAnalysisError, CoverageAnalyzer
from app.models import CoverageReport, Requirement
from app.retrieval import RetrievedTestCase


class FakeProvider:
    def __init__(self, *responses: str) -> None:
        self._responses = list(responses)
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._responses.pop(0)


class StubRetriever:
    """Returns the same fixed results for every query and records the queries."""

    def __init__(self, results: list[RetrievedTestCase]) -> None:
        self._results = results
        self.queries: list[str] = []

    def add(self, documents) -> None:  # unused in these tests
        pass

    def search(self, query: str, k: int = 5) -> list[RetrievedTestCase]:
        self.queries.append(query)
        return self._results[:k]


def make_requirement() -> Requirement:
    return Requirement(
        feature="Login",
        acceptance_criteria=["valid login works", "invalid password rejected"],
        business_rules=["lock after 5 fails"],
    )


def existing() -> list[RetrievedTestCase]:
    return [RetrievedTestCase(id="t1", text="login with valid email works", score=0.9)]


def test_analyze_returns_covered_and_gaps():
    provider = FakeProvider(
        '{"covered": ["valid login works"], "gaps": ["account lockout not tested"]}'
    )

    report = CoverageAnalyzer(provider, StubRetriever(existing())).analyze(
        make_requirement()
    )

    assert isinstance(report, CoverageReport)
    assert report.covered == ["valid login works"]
    assert report.gaps == ["account lockout not tested"]


def test_prompt_includes_requirement_and_retrieved_tests():
    """The prompt carries the requirement AND the retrieved existing tests.

    Prevents: the analyzer reasoning without the existing-coverage context.
    """
    provider = FakeProvider('{"covered": [], "gaps": []}')

    CoverageAnalyzer(provider, StubRetriever(existing())).analyze(make_requirement())

    sent = provider.prompts[0]
    assert "Login" in sent
    assert "lock after 5 fails" in sent  # business rule
    assert "login with valid email works" in sent  # retrieved existing test


def test_existing_tests_are_deduped_by_id():
    """Per-facet search is issued, but duplicate hits appear once in the prompt."""
    provider = FakeProvider('{"covered": [], "gaps": []}')
    retriever = StubRetriever(existing())

    CoverageAnalyzer(provider, retriever).analyze(make_requirement())

    assert len(retriever.queries) == 3  # 2 criteria + 1 business rule
    assert provider.prompts[0].count("login with valid email works") == 1  # deduped


def test_falls_back_to_feature_when_no_criteria_or_rules():
    """With nothing structured yet, retrieval uses the feature name."""
    provider = FakeProvider('{"covered": [], "gaps": []}')
    retriever = StubRetriever(existing())

    CoverageAnalyzer(provider, retriever).analyze(Requirement(feature="Login"))

    assert retriever.queries == ["Login"]


def test_blank_entries_are_stripped():
    provider = FakeProvider('{"covered": ["  a  ", ""], "gaps": ["  ", "b"]}')

    report = CoverageAnalyzer(provider, StubRetriever(existing())).analyze(
        make_requirement()
    )

    assert report.covered == ["a"]
    assert report.gaps == ["b"]


def test_raises_on_unparseable_output():
    provider = FakeProvider("garbage", "still garbage")

    with pytest.raises(CoverageAnalysisError):
        CoverageAnalyzer(provider, StubRetriever(existing())).analyze(make_requirement())
