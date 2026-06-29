# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Early scaffold. The FastAPI backend entrypoint (`backend/app/main.py`) exists with a root banner (`GET /`) and `GET /health` route. The `app` package is laid out with placeholder sub-packages — `api/` (`routes.py`), `agents/` (`requirement_agent.py`), `models/` (`requirement.py`), and `services/` (`requirement_parser.py`) — but these files are currently empty stubs (note: the sub-packages have no `__init__.py` yet, and a stray empty `app/requirement_parser.py` duplicates the one under `services/`). The `docs/` directory holds `git-commit-guide.md`; the `extension/`, `prompts/`, `examples/`, and `tests/` directories described in the README are intended structure and are currently empty. Most of the architecture below is planned, not yet built — treat the README's vision and roadmap as the design intent when implementing new pieces.

## Commands

All backend work happens in `backend/`:

```bash
cd backend
source .venv/bin/activate          # venv already exists at backend/.venv
pip install -r requirements.txt    # after changing dependencies

uvicorn app.main:app --reload      # run API at http://127.0.0.1:8000 (docs at /docs)
```

There is no test runner, linter, or build step configured yet. When adding tests, the README designates a top-level `tests/` directory.

## Architecture (intended)

TestCasePilot turns a software requirement into review-ready QA test cases through an agent pipeline, prioritizing depth over volume. The planned flow:

```
VS Code Extension → FastAPI Backend → Agent Orchestrator → { Requirement analyzer, RAG tool, Coverage tool } → AI provider → test cases
```

The orchestrator is meant to run a multi-step reasoning pipeline — **analyze → extract business rules → risk analysis → retrieve existing tests (RAG) → detect coverage gaps → generate → self-review** — rather than emit a flat generated list.

Key design choices that span multiple components:

- **Pluggable LLM provider.** The AI provider (OpenAI / Claude / Ollama) is configurable via environment variables; backend code should not hard-code a single provider. Credentials live in a git-ignored `backend/.env` (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `OLLAMA_HOST`). When building Claude/Anthropic integration, consult the `claude-api` skill for current model IDs and patterns.
- **RAG over existing test cases** is backed by ChromaDB — the retrieval and coverage-gap steps depend on this store.
- **Backend is the single service**; the VS Code extension is a thin TypeScript client that sends requirements to the FastAPI API.

## Conventions

- Python 3.9+ with Pydantic v2 for request/response models.
- Dependencies in `backend/requirements.txt` are fully pinned (including transitive deps); keep them pinned when adding packages.
- Backend code lives under the `app` package and is imported as `app.main:app` (run uvicorn from inside `backend/`).
