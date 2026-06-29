"""API tests for POST /requirements/risks.

Provider dependency overridden with a fake — deterministic, offline, free.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.providers import get_llm_provider


class _FakeProvider:
    def __init__(self, response: str) -> None:
        self._response = response

    def complete(self, prompt: str) -> str:
        return self._response


def test_risks_endpoint_fills_risks_via_injected_provider():
    app.dependency_overrides[get_llm_provider] = lambda: _FakeProvider(
        '{"risks": ["Brute-force attacks against the login form"]}'
    )
    try:
        client = TestClient(app)
        resp = client.post(
            "/requirements/risks",
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
        assert body["feature"] == "Login"
        assert body["risks"] == ["Brute-force attacks against the login form"]
    finally:
        app.dependency_overrides.clear()


def test_risks_endpoint_requires_markdown_field():
    client = TestClient(app)

    resp = client.post("/requirements/risks", json={})

    assert resp.status_code == 422
