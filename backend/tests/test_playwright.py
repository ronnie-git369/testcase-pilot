"""Tests for POST /tests/playwright — deterministic Playwright spec codegen.

No LLM and no provider override needed: this endpoint is a pure template over the
test cases in the request body.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_renders_a_spec_from_test_cases():
    body = {
        "feature": "Password Reset",
        "test_cases": [
            {
                "title": "link expiry",
                "type": "negative",
                "priority": "high",
                "steps": ["wait 31 minutes", "click the reset link"],
                "expected_result": "the link is rejected",
                "covers": "link expires after 30 minutes",
            }
        ],
    }
    res = client.post("/tests/playwright", json=body)
    assert res.status_code == 200

    data = res.json()
    assert data["filename"] == "password-reset.spec.ts"
    assert "import { test, expect } from '@playwright/test';" in data["code"]
    assert "test.describe('Password Reset', () => {" in data["code"]
    assert "test('link expiry', async ({ page }) => {" in data["code"]
    assert "// 1. wait 31 minutes" in data["code"]
    assert "// Expected: the link is rejected" in data["code"]
    assert "test.fixme();" in data["code"]


def test_escapes_single_quotes_in_titles():
    body = {
        "feature": "Cart",
        "test_cases": [
            {
                "title": "user's cart persists",
                "type": "positive",
                "priority": "medium",
                "steps": [],
                "expected_result": "",
                "covers": "",
            }
        ],
    }
    res = client.post("/tests/playwright", json=body)
    assert res.status_code == 200
    assert "test('user\\'s cart persists'" in res.json()["code"]


def test_empty_cases_still_returns_a_valid_skeleton():
    res = client.post("/tests/playwright", json={"feature": "Empty", "test_cases": []})
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "empty.spec.ts"
    assert "// No test cases were provided." in data["code"]
