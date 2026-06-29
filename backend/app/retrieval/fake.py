"""FakeRetriever — an in-memory TestCaseRetriever for tests and local dev.

No embeddings, no ChromaDB: it scores by word overlap (Jaccard similarity), which
is deterministic and dependency-free. Good enough to test anything that *consumes*
retrieval; the real semantic search lives in ChromaRetriever.
"""

from __future__ import annotations

from app.retrieval.base import RetrievedTestCase, TestCaseDocument


class FakeRetriever:
    """In-memory retriever scoring by shared-word (Jaccard) overlap."""

    def __init__(self) -> None:
        self._docs: list[TestCaseDocument] = []

    def add(self, documents: list[TestCaseDocument]) -> None:
        self._docs.extend(documents)

    def search(self, query: str, k: int = 5) -> list[RetrievedTestCase]:
        query_words = set(query.lower().split())
        results: list[RetrievedTestCase] = []
        for doc in self._docs:
            doc_words = set(doc.text.lower().split())
            union = query_words | doc_words
            score = len(query_words & doc_words) / len(union) if union else 0.0
            results.append(
                RetrievedTestCase(
                    id=doc.id, text=doc.text, score=score, metadata=doc.metadata
                )
            )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:k]
