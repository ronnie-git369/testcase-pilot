"""Integration test for POST /requirements/generate (the whole pipeline).

Overrides the LLM provider with a *sequenced* fake (one queued response per LLM
stage, in order) and the retriever with a FakeRetriever. Everything else — the
real parser, agents, orchestrator, and JSON validation — runs for real. This is
the full pipeline proven end-to-end over HTTP, offline.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.providers import get_llm_provider
from app.retrieval import FakeRetriever, get_retriever


class _SequencedProvider:
    def __init__(self, *responses: str) -> None:
        self._responses = list(responses)

    def complete(self, prompt: str) -> str:
        return self._responses.pop(0)


def test_generate_endpoint_runs_the_full_pipeline():
    # One response per LLM stage, in call order:
    # 1 rules, 2 risks, 3 coverage, 4 generate, 5 self-review.
    app.dependency_overrides[get_llm_provider] = lambda: _SequencedProvider(
        '{"business_rules": ["Lock account after 5 failed attempts"]}',
        '{"risks": ["Brute-force attacks"]}',
        '{"covered": ["valid login"], "gaps": ["account lockout not tested"]}',
        '{"cases": [{"title": "draft lockout", "type": "security", "priority": '
        '"high", "steps": ["x"], "expected_result": "locked", "covers": "lockout"}]}',
        '{"cases": [{"title": "Account locks after 5 failed logins", "type": '
        '"security", "priority": "high", "steps": ["enter wrong password 5 times"], '
        '"expected_result": "account is locked", "covers": "account lockout"}]}',
    )
    app.dependency_overrides[get_retriever] = lambda: FakeRetriever()
    try:
        client = TestClient(app)
        resp = client.post(
            "/requirements/generate",
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
        assert body["requirement"]["feature"] == "Login"
        assert body["requirement"]["business_rules"] == [
            "Lock account after 5 failed attempts"
        ]
        assert body["requirement"]["risks"] == ["Brute-force attacks"]
        assert body["coverage"]["gaps"] == ["account lockout not tested"]
        # final cases come from the self-review stage (the 5th response)
        assert [c["title"] for c in body["test_cases"]] == [
            "Account locks after 5 failed logins"
        ]
    finally:
        app.dependency_overrides.clear()


def test_generate_endpoint_requires_markdown_field():
    client = TestClient(app)

    resp = client.post("/requirements/generate", json={})

    assert resp.status_code == 422
