# Architecture Decision Records (ADRs)

This directory records the significant architecture decisions for TestCasePilot — what we
decided, the context, and the trade-offs — so future contributors understand *why* the
system looks the way it does.

We follow a lightweight [Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
style. Each ADR has: **Context · Decision · Consequences**, plus a status.

## Status values

- **Proposed** — under discussion
- **Accepted** — decided and in effect
- **Superseded** — replaced by a later ADR (links to it)
- **Deprecated** — no longer relevant

## Index

| # | Title | Status |
| --- | --- | --- |
| [0001](./0001-use-fastapi-for-backend.md) | Use FastAPI for the backend | Accepted |
| [0002](./0002-pluggable-llm-provider.md) | Pluggable LLM provider abstraction | Accepted |
| [0003](./0003-rag-with-chromadb.md) | RAG over existing test cases with ChromaDB | Accepted |
| [0004](./0004-agent-orchestration-pipeline.md) | Multi-step agent orchestration pipeline | Accepted |
| [0005](./0005-vscode-extension-thin-client.md) | VS Code extension as a thin client | Accepted |

## Adding a new ADR

1. Copy the structure of an existing record.
2. Number it sequentially (`000N-short-title.md`).
3. Set status to **Proposed**, fill in Context / Decision / Consequences.
4. Add a row to the index above.
5. On acceptance, update the status. Never rewrite history — supersede instead.
