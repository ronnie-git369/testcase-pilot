# ADR-0001: Use FastAPI for the backend

- **Status:** Accepted
- **Date:** 2026-06-29
- **Deciders:** Engineering

## Context

TestCasePilot needs a single backend service that exposes an HTTP API to the VS Code
extension and hosts the agent orchestration, RAG, and LLM-provider logic. Requirements:

- Python — the AI/ML and RAG ecosystem (LLM SDKs, ChromaDB) is Python-first.
- Strong, typed request/response models for structured test-case output.
- Async I/O — agent pipeline steps and LLM calls are network-bound.
- Auto-generated, interactive API docs to ease extension development.
- Low ceremony so we can move at startup speed.

## Decision

Use **FastAPI** (with **Uvicorn** as the ASGI server) as the backend framework, on
**Python 3.9+**, with **Pydantic v2** for all request/response and structured-output
models. The app is packaged under `backend/app` and run as `app.main:app`.

## Consequences

**Positive**
- Pydantic v2 integration gives typed, validated I/O for free — ideal for structured
  test-case payloads.
- Native async fits the network-bound agent/LLM pipeline.
- Automatic OpenAPI docs at `/docs` accelerate extension and integration work.
- Large ecosystem and familiarity; minimal boilerplate.

**Negative / trade-offs**
- Async correctness requires care (don't block the event loop with sync LLM SDK calls).
- FastAPI/Starlette/Pydantic version coupling — we keep dependencies fully pinned
  (including transitive) in `requirements.txt` to stay reproducible.
- A separate Python service is one more thing to deploy alongside the TS extension
  (accepted: see [ADR-0005](./0005-vscode-extension-thin-client.md)).

## Alternatives considered

- **Flask / Django REST** — more boilerplate, weaker async story, no built-in schema docs.
- **Node/Express (single language with the extension)** — would fragment the AI/RAG
  stack away from Python's mature libraries; rejected.
