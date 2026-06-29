# ADR-0005: VS Code extension as a thin client

- **Status:** Accepted
- **Date:** 2026-06-29
- **Deciders:** Engineering

## Context

The target users are QA engineers and SDETs who live in their editor. We need a delivery
surface that meets them there, while keeping the agent orchestration, RAG, and LLM logic
(all Python) in one place ([ADR-0001](./0001-use-fastapi-for-backend.md)).

A key choice: how much logic lives in the editor client vs. the backend?

## Decision

Ship a **thin VS Code extension** (TypeScript) that is a client only. It captures the
requirement (selection or input), sends it to the FastAPI backend over HTTP, and renders
the returned test cases. **All** intelligence — pipeline, RAG, provider calls,
prompt logic — stays server-side. The **backend is the single service**; the extension
holds no business logic and no credentials.

## Consequences

**Positive**
- One place to build, evolve, and test the core logic (Python backend).
- Provider keys and prompts never ship to client machines.
- The same backend API can later serve other clients (CLI, web, CI) without rework.
- Keeps the AI/RAG stack in Python while still delivering an editor-native UX.

**Negative / trade-offs**
- Requires a running/reachable backend — no fully offline editor-only mode (acceptable;
  local Ollama still allows on-prem operation).
- Two languages / areas to maintain (TS client + Python backend).
- Network round-trips for every generation; UX must handle latency/streaming gracefully.

## Alternatives considered

- **Fat extension (logic in TypeScript)** — would duplicate/port the Python AI stack into
  TS and embed credentials client-side; rejected.
- **Web app first** — viable surface, but misses the in-editor workflow that is core to the
  primary persona for MVP. The thin-client API leaves this open for later.
