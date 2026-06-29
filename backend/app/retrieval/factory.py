"""Retriever factory — selects the configured retrieval backend from the env.

`RETRIEVER` chooses the backend (default 'chroma'). Cached so the (relatively
heavy) ChromaDB client is built once per process. Used as a FastAPI dependency;
tests override it with a FakeRetriever.
"""

from __future__ import annotations

import os
from functools import lru_cache

from app.retrieval.base import TestCaseRetriever
from app.retrieval.chroma import ChromaRetriever


@lru_cache(maxsize=1)
def get_retriever() -> TestCaseRetriever:
    """Return the retriever named by the RETRIEVER env var (built once)."""
    name = os.getenv("RETRIEVER", "chroma").lower()
    if name == "chroma":
        return ChromaRetriever()
    raise ValueError(f"Unknown RETRIEVER: {name!r}")
