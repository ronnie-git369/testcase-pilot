"""API-level tests for the parse endpoint.

These exercise the full HTTP stack (routing, request validation, serialization)
via FastAPI's TestClient — not just the service. They prove the wiring, where
the unit tests prove the logic.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_parse_endpoint_returns_structured_requirement():
    """A well-formed document POSTs to 200 with every field populated."""
    md = (
        "# Feature: Login\n"
        "## User Story\n"
        "As a user I want to log in\n"
        "## Acceptance Criteria\n"
        "- valid credentials succeed"
    )

    resp = client.post("/requirements/parse", json={"markdown": md})

    assert resp.status_code == 200
    body = resp.json()
    assert body["feature"] == "Login"
    assert body["user_story"] == "As a user I want to log in"
    assert body["acceptance_criteria"] == ["valid credentials succeed"]
    assert body["business_rules"] == []  # never filled by the parser
    assert body["notes"] == []


def test_parse_endpoint_is_permissive_on_empty_markdown():
    """Empty Markdown -> 200 with the defaulted feature + breadcrumb note.

    Confirms the API mirrors the parser's permissive-but-observable behavior
    instead of rejecting the input.
    """
    resp = client.post("/requirements/parse", json={"markdown": ""})

    assert resp.status_code == 200
    body = resp.json()
    assert body["feature"] == "Untitled"
    assert any("defaulted" in note for note in body["notes"])


def test_parse_endpoint_requires_the_markdown_field():
    """Omitting the required `markdown` field is a 422 (FastAPI validation).

    Prevents: silently accepting a malformed request body. This is the API
    contract being enforced at the boundary, before any service runs.
    """
    resp = client.post("/requirements/parse", json={})

    assert resp.status_code == 422
