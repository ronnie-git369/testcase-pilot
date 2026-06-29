"""API tests for POST /requirements/business-rules.

The endpoint uses a real LLM in production, but here we override the provider
dependency with a fake — so the test is deterministic, offline, and free. This
is the concrete payoff of injecting the provider via FastAPI `Depends`.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.providers import get_llm_provider


class _FakeProvider:
    """Returns a fixed completion; structurally an LLMProvider."""

    def __init__(self, response: str) -> None:
        self._response = response

    def complete(self, prompt: str) -> str:
        return self._response


def test_business_rules_endpoint_fills_rules_via_injected_provider():
    """Markdown in -> parsed Requirement with business_rules filled by the agent."""
    app.dependency_overrides[get_llm_provider] = lambda: _FakeProvider(
        '{"business_rules": ["Lock the account after 5 failed attempts"]}'
    )
    try:
        client = TestClient(app)
        resp = client.post(
            "/requirements/business-rules",
            json={
                "markdown": (
                    "# Feature: Login\n"
                    "## Acceptance Criteria\n"
                    "- account locks after 5 failed attempts"
                )
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["feature"] == "Login"  # deterministic parse step still ran
        assert body["business_rules"] == ["Lock the account after 5 failed attempts"]
    finally:
        app.dependency_overrides.clear()  # don't leak the override into other tests


def test_business_rules_endpoint_requires_markdown_field():
    """Missing `markdown` is a 422, same contract as /parse."""
    client = TestClient(app)

    resp = client.post("/requirements/business-rules", json={})

    assert resp.status_code == 422
