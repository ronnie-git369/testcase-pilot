"""Unit tests for the retrieval port via FakeRetriever.

These prove the retrieval *contract* (ranking, k-limit, empties) deterministically
and offline. The real ChromaRetriever gets its own (skip-guarded) tests.
"""

from app.retrieval import FakeRetriever, TestCaseDocument


def make_store() -> FakeRetriever:
    retriever = FakeRetriever()
    retriever.add(
        [
            TestCaseDocument(id="t1", text="user logs in with valid email and password"),
            TestCaseDocument(id="t2", text="user resets a forgotten password via email"),
            TestCaseDocument(id="t3", text="admin exports the monthly sales report"),
        ]
    )
    return retriever


def test_search_returns_most_similar_first():
    """The closest document by word overlap ranks first."""
    results = make_store().search("login with email and password", k=3)

    assert results[0].id == "t1"  # most overlap
    assert results[0].score >= results[1].score >= results[2].score


def test_search_respects_k_limit():
    """At most k results are returned."""
    results = make_store().search("password", k=2)

    assert len(results) == 2


def test_search_on_empty_store_returns_empty_list():
    """Querying before anything is indexed is empty, not an error."""
    assert FakeRetriever().search("anything") == []


def test_scores_are_normalized_between_zero_and_one():
    """Jaccard scores stay in [0, 1]."""
    for result in make_store().search("user password", k=3):
        assert 0.0 <= result.score <= 1.0
