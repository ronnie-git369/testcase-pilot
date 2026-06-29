# TestCasePilot — API Reference & Guide

> How the HTTP API is built, how a request flows through it, and how to run it.
>
> Companion docs: [Architecture](./architecture.md) · [Milestone Walkthrough](./milestones.md) ·
> [ADRs](./adr/README.md)

---

## 1. Overview

The backend is a **FastAPI** application that exposes TestCasePilot's logic over HTTP.
Today it serves a deterministic, LLM-free endpoint that turns a Markdown requirement
into a structured `Requirement` object, plus basic service/health routes.

| Aspect | Detail |
| --- | --- |
| Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Server | [Uvicorn](https://www.uvicorn.org/) (ASGI) |
| Data models | Pydantic v2 |
| App object | `app.main:app` (run from inside `backend/`) |
| Base URL (dev) | `http://127.0.0.1:8000` |
| Interactive docs | `/docs` (Swagger UI) · `/redoc` (ReDoc) |

---

## 2. How to turn on the API

### Prerequisites
- Python 3.9+
- The project's virtual environment at `backend/.venv` with dependencies installed.

### First-time setup
```bash
cd backend
python3 -m venv .venv               # only if .venv doesn't exist yet
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt     # runtime deps
pip install -r requirements-dev.txt # dev/test deps (pytest, httpx) — optional
```

### Run the server
From inside `backend/` (so the `app` package is importable):
```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

- `app.main:app` → import the `app` object from `app/main.py`.
- `--reload` → auto-restart on code changes (development only; omit in production).
- Optional flags: `--port 8000` (default), `--host 0.0.0.0` (expose on your network).

Stop the server with **Ctrl+C**.

### Verify it's up
```bash
curl http://127.0.0.1:8000/health          # {"status":"healthy"}
```
Then open **http://127.0.0.1:8000/docs** in a browser for the interactive UI.

> **Tip (inside a Claude Code session):** prefix the command with `!` to run it in the
> session, e.g. `! cd backend && source .venv/bin/activate && uvicorn app.main:app --reload`.

---

## 3. How the API is made (architecture)

The API follows **Clean Architecture**: dependencies point *inward*, and the web
framework sits at the outer edge. None of the inner layers import FastAPI.

```
 FastAPI / Uvicorn                         (frameworks / drivers)
   │
   ▼
 app/main.py            composition root — creates the app, includes routers
   │                    (no route logic lives here)
   ▼
 app/api/routes.py      interface adapter — THIN routes: HTTP <-> domain
   │                    request validation, calls a service, returns a model
   ▼
 app/services/…         application logic — RequirementParserService
   │
   ▼
 app/models/…           domain entities — Requirement (pure data)
```

### The pieces

**`app/main.py` — the composition root.** Creates the `FastAPI()` app and mounts
routers via `include_router`. It deliberately contains no endpoint logic, so the
entrypoint stays small and stable as features grow.

```python
app = FastAPI(title="TestCasePilot API", version="0.1.0", description="...")
app.include_router(api_router)        # mounts /requirements/parse
```

**`app/api/routes.py` — the thin adapter.** An `APIRouter` groups the routes under a
prefix and a docs tag. Each handler does only: validate input → call a service → return
a model.

```python
router = APIRouter(prefix="/requirements", tags=["requirements"])

class ParseRequirementRequest(BaseModel):      # request DTO (API layer)
    markdown: str = Field(...)

def get_parser() -> RequirementParserService:  # dependency provider
    return RequirementParserService()

@router.post("/parse", response_model=Requirement)
def parse_requirement(request, parser = Depends(get_parser)):
    return parser.parse(request.markdown)
```

### Three deliberate design choices

1. **Dependency Injection (`Depends`).** The route *receives* its service instead of
   constructing one. This makes the route testable (override via
   `app.dependency_overrides`) and is the seam where a configured/provider-aware service
   will later be wired in.
2. **DTO vs domain entity.** `ParseRequirementRequest` (an HTTP input shape) lives in
   the API layer; `Requirement` (a reusable domain entity) lives in `app/models/`.
   Different layers, different reasons to change.
3. **`response_model=Requirement`.** FastAPI uses it to serialize the result, *filter*
   the output to exactly the model's fields, and publish the response schema to `/docs`.

---

## 4. How a request works (lifecycle)

Walking a `POST /requirements/parse` call end to end:

```
 client
   │  POST /requirements/parse   { "markdown": "..." }
   ▼
 FastAPI router  ── matches the path + method
   │
   ▼
 request validation  ── body parsed into ParseRequirementRequest
   │                    (missing/!string `markdown` → 422 before any logic runs)
   ▼
 Depends(get_parser) ── builds a RequirementParserService
   │
   ▼
 parser.parse(markdown) ── deterministic, single-pass O(n) tokenizer → Requirement
   │
   ▼
 response_model=Requirement ── serialize + filter → JSON
   │
   ▼
 client  ◄── 200 OK  { feature, user_story, acceptance_criteria, business_rules, risks, notes }
```

The endpoint is **deterministic**: same input → same output, no LLM, no I/O, no side
effects.

---

## 5. Endpoint reference

### `GET /`
Service banner.

```bash
curl http://127.0.0.1:8000/
```
```json
{ "service": "TestCasePilot API", "status": "ok", "version": "0.1.0" }
```

### `GET /health`
Liveness/health check.

```bash
curl http://127.0.0.1:8000/health
```
```json
{ "status": "healthy" }
```

### `POST /requirements/parse`
Parse a Markdown requirement into a structured `Requirement`.

**Request body** (`application/json`):

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `markdown` | string | yes | Raw Markdown requirement text |

**Responses:**

| Status | When | Body |
| --- | --- | --- |
| `200 OK` | Always, for any string input (incl. empty) | a `Requirement` |
| `422 Unprocessable Entity` | `markdown` missing or not a string | FastAPI validation error |

**Example — well-formed input:**
```bash
curl -X POST http://127.0.0.1:8000/requirements/parse \
  -H "Content-Type: application/json" \
  -d '{"markdown":"# Feature: Login\n## User Story\nAs a user I want to log in\n## Acceptance Criteria\n- valid credentials succeed\n- invalid password is rejected"}'
```
```json
{
  "feature": "Login",
  "user_story": "As a user I want to log in",
  "acceptance_criteria": [
    "valid credentials succeed",
    "invalid password is rejected"
  ],
  "business_rules": [],
  "risks": [],
  "notes": []
}
```

**Example — empty input (permissive but observable):**
```bash
curl -X POST http://127.0.0.1:8000/requirements/parse \
  -H "Content-Type: application/json" -d '{"markdown":""}'
```
```json
{
  "feature": "Untitled",
  "user_story": "",
  "acceptance_criteria": [],
  "business_rules": [],
  "risks": [],
  "notes": ["No feature heading found; defaulted to 'Untitled'."]
}
```
The API never crashes on malformed-but-present input; it returns a best-effort
`Requirement` and records what it had to assume in `notes`.

**Example — missing required field → 422:**
```bash
curl -i -X POST http://127.0.0.1:8000/requirements/parse \
  -H "Content-Type: application/json" -d '{}'
# HTTP/1.1 422 Unprocessable Entity
```

---

## 6. Schemas

### `ParseRequirementRequest` (request DTO)
```jsonc
{ "markdown": "string (required)" }
```

### `Requirement` (response / domain entity)
| Field | Type | Filled by | Notes |
| --- | --- | --- | --- |
| `feature` | string | parser | Required; defaults to `"Untitled"` if no heading found |
| `user_story` | string | parser | `""` if no `## User Story` section |
| `acceptance_criteria` | string[] | parser | bullets under `## Acceptance Criteria` |
| `business_rules` | string[] | *future agent* | always `[]` today |
| `risks` | string[] | *future agent* | always `[]` today |
| `notes` | string[] | parser | breadcrumbs (e.g. defaulted-feature note) |

The expected input Markdown shape and parsing rules are documented in the
[Milestone Walkthrough §3.2–3.3](./milestones.md).

---

## 7. Errors

- **422 Unprocessable Entity** — request body fails validation (e.g. `markdown` missing
  or wrong type). FastAPI generates this automatically from the request model, *before*
  any service code runs. The body lists which field failed and why.
- **Malformed-but-present Markdown** is **not** an error: by design the parser is
  permissive and returns `200` with breadcrumbs in `notes`.

---

## 8. Testing the API

API-level tests use FastAPI's `TestClient` (backed by `httpx`) and exercise the full
HTTP stack — routing, validation, and serialization — without a running server.

```bash
cd backend
source .venv/bin/activate
pytest                 # runs unit + API tests (config in pyproject.toml)
pytest tests/test_api.py -v   # just the API tests
```

`tests/test_api.py` covers: a structured 200 response, the permissive-empty case, and
the 422-on-missing-field case. (API tests prove the *wiring*; the service's unit tests
prove the *logic*.)

---

## 9. File map

```
backend/app/
├── main.py              # FastAPI app + router wiring (composition root)
├── api/
│   ├── __init__.py      # exports the router
│   └── routes.py        # APIRouter, ParseRequirementRequest, get_parser, /parse
├── services/
│   └── requirement_parser.py   # RequirementParserService.parse()
└── models/
    └── requirement.py   # Requirement (response model / domain entity)
backend/tests/test_api.py       # TestClient-based API tests
```

---

## 10. What's coming

The same patterns (router, request/response models, dependency injection) will host the
agentic pipeline:

- `POST /generate` — the orchestrator endpoint (analyze → extract rules → risk →
  retrieve (RAG) → coverage gaps → generate → self-review). See
  [ADR-0004](./adr/0004-agent-orchestration-pipeline.md).
- A pluggable LLM provider injected via the same `Depends` mechanism. See
  [ADR-0002](./adr/0002-pluggable-llm-provider.md).
