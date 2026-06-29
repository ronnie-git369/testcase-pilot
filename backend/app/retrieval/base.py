"""TestCaseRetriever — the port (abstraction) for similarity search over tests.

Consumers (the future CoverageAnalyzer / TestGeneratorAgent and the search
endpoint) depend on THIS Protocol, never on ChromaDB. Concrete adapters
(ChromaRetriever) and a FakeRetriever (tests) implement it.

This is the 'R' in RAG: given a query (a requirement), return the most similar
existing test cases so they can ground later steps.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class TestCaseDocument(BaseModel):
    """An existing test case to index into the store."""

    id: str
    text: str
    metadata: dict[str, str] = Field(default_factory=dict)


class RetrievedTestCase(BaseModel):
    """A test case returned from a similarity search."""

    id: str
    text: str
    score: float  # normalized 0..1; higher = more similar
    metadata: dict[str, str] = Field(default_factory=dict)


@runtime_checkable
class TestCaseRetriever(Protocol):
    """Minimal interface every retrieval backend must satisfy."""

    def add(self, documents: list[TestCaseDocument]) -> None:
        """Index (or upsert) the given test-case documents."""
        ...

    def search(self, query: str, k: int = 5) -> list[RetrievedTestCase]:
        """Return up to `k` documents most similar to `query`, best first."""
        ...
