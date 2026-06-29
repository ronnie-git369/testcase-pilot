"""HTTP routes for retrieval (the 'R' in RAG): index and search existing tests.

Thin adapters over the TestCaseRetriever port. The retriever is injected via
`Depends(get_retriever)`, so tests swap in a FakeRetriever with no ChromaDB.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.retrieval import RetrievedTestCase, TestCaseDocument, TestCaseRetriever
from app.retrieval.factory import get_retriever

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


class IndexRequest(BaseModel):
    """Request body for POST /retrieval/index."""

    documents: list[TestCaseDocument]


class IndexResponse(BaseModel):
    """How many documents were indexed."""

    indexed: int


class SearchRequest(BaseModel):
    """Request body for POST /retrieval/search."""

    query: str = Field(..., description="Text to find similar test cases for.")
    k: int = Field(default=5, ge=1, le=50, description="Max results to return.")


@router.post("/index", response_model=IndexResponse)
def index_test_cases(
    request: IndexRequest,
    retriever: TestCaseRetriever = Depends(get_retriever),
) -> IndexResponse:
    """Index (or upsert) existing test cases for later similarity search."""
    retriever.add(request.documents)
    return IndexResponse(indexed=len(request.documents))


@router.post("/search", response_model=list[RetrievedTestCase])
def search_test_cases(
    request: SearchRequest,
    retriever: TestCaseRetriever = Depends(get_retriever),
) -> list[RetrievedTestCase]:
    """Return the indexed test cases most similar to the query."""
    return retriever.search(request.query, k=request.k)
