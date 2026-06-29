# ADR-0003: RAG over existing test cases with ChromaDB

- **Status:** Accepted
- **Date:** 2026-06-29
- **Deciders:** Engineering

## Context

A core differentiator is grounding generation in a team's **existing** test cases rather
than generating in a vacuum. This requires semantic retrieval so the pipeline can:

- Retrieve test cases similar to the incoming requirement (the **retrieve** step).
- Compare intended coverage against what already exists (the **gap-detection** step).
- Match the team's existing style and avoid re-deriving cases they already have.

We need a vector store that is easy to embed in a Python service, runs locally with no
heavy infrastructure for the MVP, and is simple to operate.

## Decision

Use **ChromaDB** as the vector store backing retrieval-augmented generation (RAG) over
the corpus of existing test cases. The retrieval and coverage-gap steps of the agent
pipeline depend on this store. Test cases are ingested and embedded into Chroma; the
pipeline queries it for semantically similar cases at generation time.

## Consequences

**Positive**
- Python-native, embeddable, minimal ops — fits a single FastAPI service and startup speed.
- Local-first aligns with the on-prem/privacy story ([ADR-0002](./0002-pluggable-llm-provider.md)).
- Good enough recall for similarity search over a team-sized test corpus.

**Negative / trade-offs**
- Not built for very large multi-tenant scale; revisit (e.g. pgvector, Qdrant, managed
  vector DB) if/when we outgrow a single-team corpus.
- Retrieval quality depends on embedding choice and corpus hygiene — ingestion tooling and
  overlap metrics are needed to keep it honest.
- Requires an ingestion/refresh workflow to keep the index current with the test corpus.

## Alternatives considered

- **pgvector (Postgres)** — great if we already ran Postgres; adds a DB dependency we
  don't yet need for MVP.
- **Qdrant / Weaviate / managed services** — more scalable, more operational overhead;
  premature for a single-team MVP.
- **Keyword search (no vectors)** — misses semantic similarity that the gap-detection step
  relies on; rejected.
