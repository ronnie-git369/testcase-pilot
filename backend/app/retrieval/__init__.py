"""Retrieval layer — similarity search over existing test cases (the 'R' in RAG).

`TestCaseRetriever` is the port; adapters (ChromaRetriever) and a FakeRetriever
plug into it. Consumers depend on the abstraction, not on ChromaDB.
"""

from app.retrieval.base import (
    RetrievedTestCase,
    TestCaseDocument,
    TestCaseRetriever,
)
from app.retrieval.chroma import ChromaRetriever
from app.retrieval.factory import get_retriever
from app.retrieval.fake import FakeRetriever

__all__ = [
    "TestCaseRetriever",
    "TestCaseDocument",
    "RetrievedTestCase",
    "FakeRetriever",
    "ChromaRetriever",
    "get_retriever",
]
