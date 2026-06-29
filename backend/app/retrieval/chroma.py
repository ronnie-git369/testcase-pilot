"""ChromaRetriever — TestCaseRetriever backed by ChromaDB (embedded).

Uses ChromaDB's default local embedding (an ONNX MiniLM model, downloaded once)
so similarity search is semantic and fully offline — no API key. Persists to
CHROMA_PATH so an ingested suite survives restarts; pass `in_memory=True` for
ephemeral use (tests).
"""

from __future__ import annotations

import os

import chromadb

from app.retrieval.base import RetrievedTestCase, TestCaseDocument

DEFAULT_PATH = ".chroma"
DEFAULT_COLLECTION = "testcases"
# Chroma rejects empty metadata dicts, so we stash a placeholder and strip it.
_PLACEHOLDER_KEY = "_"


class ChromaRetriever:
    """Semantic retriever over existing test cases using ChromaDB."""

    def __init__(
        self,
        path: str | None = None,
        collection: str | None = None,
        in_memory: bool = False,
    ) -> None:
        if in_memory:
            self._client = chromadb.EphemeralClient()
        else:
            self._client = chromadb.PersistentClient(
                path=path or os.getenv("CHROMA_PATH", DEFAULT_PATH)
            )
        self._collection = self._client.get_or_create_collection(
            name=collection or os.getenv("CHROMA_COLLECTION", DEFAULT_COLLECTION)
        )

    def add(self, documents: list[TestCaseDocument]) -> None:
        if not documents:
            return
        self._collection.add(
            ids=[d.id for d in documents],
            documents=[d.text for d in documents],
            metadatas=[d.metadata or {_PLACEHOLDER_KEY: "1"} for d in documents],
        )

    def search(self, query: str, k: int = 5) -> list[RetrievedTestCase]:
        result = self._collection.query(query_texts=[query], n_results=k)

        # Chroma returns one list per query; we sent a single query.
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        dists = result.get("distances", [[]])[0]
        metas = result.get("metadatas", [[]])[0]

        retrieved: list[RetrievedTestCase] = []
        for id_, text, dist, meta in zip(ids, docs, dists, metas):
            # Convert L2 distance (smaller = closer) to a 0..1 score.
            score = 1.0 / (1.0 + float(dist))
            clean_meta = {
                key: str(value)
                for key, value in (meta or {}).items()
                if key != _PLACEHOLDER_KEY
            }
            retrieved.append(
                RetrievedTestCase(id=id_, text=text, score=score, metadata=clean_meta)
            )
        return retrieved
