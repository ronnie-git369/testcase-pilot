"""API tests for the /retrieval endpoints.

The retriever dependency is overridden with a single shared FakeRetriever, so
index-then-search works in-process with no ChromaDB, no embeddings, no disk.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.retrieval import FakeRetriever
from app.retrieval.factory import get_retriever


def test_index_then_search_roundtrip():
    """Documents indexed via /index are findable via /search."""
    fake = FakeRetriever()
    app.dependency_overrides[get_retriever] = lambda: fake
    try:
        client = TestClient(app)

        index_resp = client.post(
            "/retrieval/index",
            json={
                "documents": [
                    {"id": "t1", "text": "user logs in with valid email and password"},
                    {"id": "t2", "text": "admin exports the monthly sales report"},
                ]
            },
        )
        assert index_resp.status_code == 200
        assert index_resp.json() == {"indexed": 2}

        search_resp = client.post(
            "/retrieval/search",
            json={"query": "login with email and password", "k": 1},
        )
        assert search_resp.status_code == 200
        results = search_resp.json()
        assert len(results) == 1
        assert results[0]["id"] == "t1"
        assert 0.0 <= results[0]["score"] <= 1.0
    finally:
        app.dependency_overrides.clear()


def test_search_validates_k_bounds():
    """k must be within [1, 50] — FastAPI rejects out-of-range with 422."""
    app.dependency_overrides[get_retriever] = lambda: FakeRetriever()
    try:
        client = TestClient(app)
        resp = client.post("/retrieval/search", json={"query": "x", "k": 0})
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()
