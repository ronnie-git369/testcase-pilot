"""Integration test for the real ChromaRetriever (semantic search).

Uses an in-memory Chroma client, but still needs the default embedding model
(an ONNX MiniLM download on first use). If Chroma or the model can't be loaded
(e.g. no network in CI), the test SKIPS rather than fails — keeping the suite
green everywhere.
"""

import pytest

from app.retrieval.base import TestCaseDocument


@pytest.fixture
def chroma():
    from app.retrieval.chroma import ChromaRetriever

    try:
        retriever = ChromaRetriever(in_memory=True)
        retriever.add(
            [
                TestCaseDocument(
                    id="t1",
                    text="user logs in with a valid email and correct password",
                    metadata={"feature": "Login"},
                ),
                TestCaseDocument(
                    id="t2", text="admin exports the monthly sales report as CSV"
                ),
            ]
        )
    except Exception as exc:  # chromadb or embedding model unavailable
        pytest.skip(f"ChromaDB/embedding unavailable: {exc}")
    return retriever


def test_semantic_search_finds_the_relevant_case(chroma):
    """A paraphrase (no shared keywords) still retrieves the right test.

    This is what embeddings buy over keyword matching: 'sign in using credentials'
    matches the login case even though the words differ.
    """
    results = chroma.search("sign in using account credentials", k=1)

    assert len(results) == 1
    assert results[0].id == "t1"
    assert 0.0 <= results[0].score <= 1.0
    assert results[0].metadata.get("feature") == "Login"
