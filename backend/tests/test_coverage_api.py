"""API test for POST /requirements/coverage (the three-stage pipeline).

Both the LLM provider and the retriever are overridden with fakes. The provider
serves a *sequence*: the first completion is the business-rules extraction, the
second is the coverage analysis (FastAPI caches get_llm_provider within a request,
so both agents share this one provider instance).
"""

from fastapi.testclient import TestClient

from app.main import app
from app.providers import get_llm_provider
from app.retrieval import FakeRetriever, get_retriever


class _SequencedProvider:
    """Returns queued responses in order — structurally an LLMProvider."""

    def __init__(self, *responses: str) -> None:
        self._responses = list(responses)

    def complete(self, prompt: str) -> str:
        return self._responses.pop(0)


def test_coverage_endpoint_runs_parse_then_rules_then_coverage():
    app.dependency_overrides[get_llm_provider] = lambda: _SequencedProvider(
        '{"business_rules": ["Lock account after 5 failed attempts"]}',  # call 1
        '{"covered": ["valid login"], "gaps": ["account lockout not tested"]}',  # call 2
    )
    app.dependency_overrides[get_retriever] = lambda: FakeRetriever()
    try:
        client = TestClient(app)
        resp = client.post(
            "/requirements/coverage",
            json={
                "markdown": (
                    "# Feature: Login\n"
                    "## Acceptance Criteria\n"
                    "- valid login\n"
                    "- lockout after 5 fails"
                )
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["covered"] == ["valid login"]
        assert body["gaps"] == ["account lockout not tested"]
    finally:
        app.dependency_overrides.clear()


def test_coverage_endpoint_requires_markdown_field():
    client = TestClient(app)

    resp = client.post("/requirements/coverage", json={})

    assert resp.status_code == 422
