# TestCasePilot — System Architecture

> Status: Living document. Last updated 2026-06-29.
> Companion docs: [Product Requirements](./product-requirements.md) ·
> [Architecture Decision Records](./adr/README.md) · [Diagrams](./diagrams/README.md)

---

## Project Vision

QA engineers spend a disproportionate share of their time turning prose requirements
into structured test cases. The mechanical parts of that work — restating acceptance
criteria, enumerating the obvious happy paths, formatting tickets — are tedious, while
the parts that actually catch defects — reasoning about business rules, edge cases, and
the gaps in *existing* coverage — get squeezed. Generic "generate test cases from this
text" tooling makes the imbalance worse: it floods reviewers with shallow, redundant
cases that a QA lead has to triage by hand.

TestCasePilot is an agentic AI QA assistant that behaves like a senior QA engineer
rather than a text generator. Given a software requirement, it runs a multi-step
reasoning pipeline — analyze intent, extract business rules, assess risk, retrieve the
team's existing test cases, detect coverage gaps, generate, and self-review — before it
presents anything. The guiding principle is **depth over volume**: fewer, higher-signal
test cases that a reviewer would actually sign off on, each traceable to a business rule
or an identified risk.

The product meets engineers where they work. A thin VS Code extension is the primary
surface; a FastAPI backend does the orchestration and retrieval; and the LLM provider is
pluggable (OpenAI, Anthropic Claude, or a local Ollama model) so teams can choose their
cost, latency, and data-residency trade-offs without code changes. Over time the same
retrieval-augmented foundation becomes a living map of a team's test coverage, not just a
one-shot generator.

## Target Users

| User | Role & context | What they need from TestCasePilot |
| --- | --- | --- |
| **QA Engineer** (primary) | Writes and maintains test cases from requirements and tickets | Turn a requirement into review-ready cases without hand-enumerating every path; surface edge cases they might miss |
| **QA Lead / Test Manager** | Reviews and signs off on test coverage | High-signal output worth reviewing; traceability from case → rule → risk; visibility into coverage gaps |
| **Software Engineer / SDET** | Implements features, writes adjacent tests | Quick generation of cases for a requirement inside the editor; consistency with the team's existing test style |
| **Product Manager / BA** (secondary) | Authors requirements and acceptance criteria | A feedback loop that exposes ambiguous or untestable requirements early |

Primary design target is the **QA Engineer working in VS Code** on a team that already
has a corpus of existing test cases worth mining. Secondary stakeholders (leads, PMs)
consume the output and the coverage signal.

## User Workflow

```
1. Select / paste a requirement in the VS Code extension
2. (Optional) choose scope hints — module, priority, provider
3. Extension POSTs the requirement to the FastAPI backend
4. Backend runs the agent pipeline (see Agent Workflow below)
5. Extension renders review-ready test cases with rationale + coverage notes
6. Engineer edits / accepts / rejects cases inline
7. Accepted cases are exported (clipboard, file, or test-management tool)
```

The interaction is **request → review → refine**. TestCasePilot never silently commits
anything; the engineer stays the decision-maker and the tool is accountable for *why*
each case exists (which rule, which risk, which gap it fills).

## Agent Workflow

The orchestrator runs a deliberate multi-step pipeline rather than a single generate
call. Each step's output feeds the next, and the final self-review can loop back.

```
Requirement
    │
    ▼
1. Analyze        → intent, scope, actors, preconditions
    │
    ▼
2. Extract rules  → explicit + implicit business rules the system must enforce
    │
    ▼
3. Risk analysis  → prioritize by impact × likelihood; flag high-risk areas
    │
    ▼
4. Retrieve (RAG) → pull semantically similar existing test cases from ChromaDB
    │
    ▼
5. Gap detection  → compare intended coverage vs. what already exists
    │
    ▼
6. Generate       → author new cases targeting rules + risks + gaps
    │
    ▼
7. Self-review    → critique for redundancy, testability, coverage; revise
    │
    ▼
Review-ready test cases (+ rationale, coverage notes)
```

Design intent for the pipeline:

- **Traceability** — every generated case links back to a rule, a risk, or a gap.
- **RAG-grounded** — generation is conditioned on the team's real test corpus so output
  matches existing style and avoids re-deriving cases that already exist.
- **Self-critique before output** — the review step is what keeps volume down and signal
  up; it is a first-class stage, not an afterthought.

See [`diagrams/agent-pipeline.md`](./diagrams/agent-pipeline.md) for the rendered flow.

## Features (MVP vs Future)

### MVP

- Single-requirement → test-case generation via REST API (`POST /generate`)
- Multi-step agent pipeline: analyze → extract → risk → retrieve → gap → generate → review
- Pluggable LLM provider (OpenAI / Claude / Ollama) via environment config
- ChromaDB-backed RAG over an ingested corpus of existing test cases
- Structured, typed output (Pydantic v2) with per-case rationale
- VS Code extension: send selection/requirement, render results, copy/export
- `/health` and service banner; interactive API docs at `/docs`

### Future

- Batch / bulk requirement processing
- Two-way sync with test-management tools (Jira/Xray, TestRail, Azure Test Plans)
- Coverage dashboard — visualize gaps across a module or release
- Requirement quality linting (flag ambiguous / untestable requirements)
- Team feedback loop: accepted/rejected signals fine-tune retrieval and prompts
- Multi-language / localization of generated cases
- Role-based access, audit log, and self-hosted deployment guide
- Automated regression-suite suggestions from diffs

## High-Level Architecture Diagram

```
                         User (QA Engineer)
                                │
                                ▼
                    ┌───────────────────────┐
                    │   VS Code Extension    │  (thin TypeScript client)
                    └───────────┬───────────┘
                                │  HTTP (JSON)
                                ▼
                    ┌───────────────────────┐
                    │    FastAPI Backend     │  (single service)
                    │  api/ · models/ ·      │
                    │  agents/ · services/   │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │   Agent Orchestrator   │
                    │  analyze → … → review  │
                    └───┬───────────┬───────┬┘
                        ▼           ▼       ▼
                 ┌──────────┐ ┌─────────┐ ┌──────────┐
                 │Requirement│ │RAG Tool │ │ Coverage │
                 │ Analyzer  │ │(Chroma) │ │   Tool   │
                 └──────────┘ └────┬────┘ └──────────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │  ChromaDB   │  (existing test-case vectors)
                            └─────────────┘
                                   │
                                   ▼
                    ┌───────────────────────┐
                    │  LLM Provider (plug)   │
                    │ OpenAI / Claude / Ollama│
                    └───────────┬───────────┘
                                ▼
                       Review-ready Test Cases
```

A richer, rendered version (Mermaid) lives in
[`diagrams/system-context.md`](./diagrams/system-context.md).

## Technology Stack

| Layer | Technology | Notes |
| --- | --- | --- |
| Client | VS Code Extension · TypeScript | Thin client; all logic server-side |
| API | FastAPI · Uvicorn · Python 3.9+ | Single backend service ([ADR-0001](./adr/0001-use-fastapi-for-backend.md)) |
| Data models | Pydantic v2 | Typed request/response + structured output |
| Orchestration | Custom agent pipeline | Multi-step reasoning ([ADR-0004](./adr/0004-agent-orchestration-pipeline.md)) |
| Retrieval | RAG · ChromaDB | Vector store over existing tests ([ADR-0003](./adr/0003-rag-with-chromadb.md)) |
| LLM provider | OpenAI · Anthropic Claude · Ollama | Pluggable via env ([ADR-0002](./adr/0002-pluggable-llm-provider.md)) |
| Config / secrets | Environment variables · git-ignored `backend/.env` | `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `OLLAMA_HOST` |
| Dependencies | Fully pinned `requirements.txt` | Incl. transitive deps |

## Project Roadmap

**Phase 0 — Scaffold** *(current)*
- [x] FastAPI entrypoint (`app/main.py`: root banner + `/health`)
- [x] Package layout: `api/`, `agents/`, `models/`, `services/` (placeholders)
- [x] Pinned backend dependencies
- [x] Architecture & product docs (this suite)

**Phase 1 — MVP backend**
- [ ] Requirement request/response Pydantic models
- [ ] `POST /generate` route wired through the API layer
- [ ] Pluggable LLM provider abstraction
- [ ] Agent pipeline (analyze → extract → risk → generate → review), RAG-light
- [ ] ChromaDB integration + test-corpus ingestion

**Phase 2 — RAG & coverage**
- [ ] Full RAG retrieval step over the ingested corpus
- [ ] Coverage-gap detection tool
- [ ] Traceability metadata on every generated case

**Phase 3 — Client & polish**
- [ ] VS Code extension (send requirement, render, export)
- [ ] Example requirements + golden test cases
- [ ] Test suite + CI

**Phase 4 — Beyond MVP**
- [ ] Test-management integrations
- [ ] Coverage dashboard & requirement linting
- [ ] Feedback-driven retrieval/prompt tuning

> Roadmap items are tracked at a high level here; the authoritative acceptance criteria
> live in the [PRD](./product-requirements.md).
