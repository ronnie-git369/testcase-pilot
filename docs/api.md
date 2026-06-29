# TestCasePilot — API Reference & Guide

> How the HTTP API is built, how a request flows through it, and how to run it.
>
> Companion docs: [Architecture](./architecture.md) · [Milestone Walkthrough](./milestones.md) ·
> [ADRs](./adr/README.md)

---

## 1. Overview

The backend is a **FastAPI** application that exposes TestCasePilot's logic over HTTP.
It serves a deterministic parse endpoint (Markdown → structured `Requirement`),
LLM-backed analysis endpoints (business rules, risks, and retrieval-grounded coverage
gaps), a full **orchestrator** endpoint that runs the whole pipeline and returns
generated test cases, retrieval endpoints for semantic search over existing tests (RAG),
and basic service/health routes. The deterministic and probabilistic parts are cleanly
separated (see §3).

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

### LLM provider (only for the analysis endpoints)

`GET /`, `/health`, and `POST /requirements/parse` are deterministic and need **no**
provider. The LLM-backed endpoints (`/requirements/business-rules`, `/requirements/risks`)
call a language model selected by environment variables (ADR-0002):

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_PROVIDER` | `ollama` | Which backend to use (only `ollama` is implemented today) |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.1` | Model name |

For the default (Ollama), install [Ollama](https://ollama.com), then:
```bash
ollama pull llama3.1 && ollama serve
```
Without a reachable provider, the deterministic routes still work; the analysis
endpoints return a `502`/`500`-class error when the model can't be reached.

### Retrieval (RAG) configuration

The `/retrieval/*` endpoints use a vector store selected by environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `RETRIEVER` | `chroma` | Retrieval backend (only `chroma` is implemented today) |
| `CHROMA_PATH` | `.chroma` | On-disk location of the persistent index |
| `CHROMA_COLLECTION` | `testcases` | Collection name |

ChromaDB is embedded (no separate server) and uses a small **local** embedding model,
downloaded once on first use — no API key. The `.chroma/` directory is generated data
and is git-ignored.

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

### `POST /requirements/business-rules`
Parse the Markdown, then fill `business_rules` using the LLM agent
(`BusinessRuleExtractor`). **Requires a reachable LLM provider** (see §2).

This composes two pipeline stages: deterministic `parse` → probabilistic
`extract`.

**Request body:** same as `/parse` — `{ "markdown": "..." }`.

**Responses:**

| Status | When | Body |
| --- | --- | --- |
| `200 OK` | Rules extracted (or none found) | a `Requirement` with `business_rules` populated |
| `422` | `markdown` missing/not a string | validation error |
| `500`-class | LLM unreachable or unparseable after a retry | error |

```bash
curl -X POST http://127.0.0.1:8000/requirements/business-rules \
  -H "Content-Type: application/json" \
  -d '{"markdown":"# Feature: Login\n## Acceptance Criteria\n- account locks after 5 failed attempts"}'
```
```json
{
  "feature": "Login",
  "user_story": "",
  "acceptance_criteria": ["account locks after 5 failed attempts"],
  "business_rules": ["Lock the account after 5 consecutive failed attempts"],
  "risks": [],
  "notes": []
}
```

### `POST /requirements/risks`
Parse the Markdown, then fill `risks` using the LLM agent (`RiskAnalyzer`). If the
`Requirement` already carries `business_rules`, the prompt uses them for sharper risks.
**Requires a reachable LLM provider** (see §2).

**Request body:** same as `/parse` — `{ "markdown": "..." }`.

**Responses:** same status table as `/business-rules`, but populates `risks`.

```bash
curl -X POST http://127.0.0.1:8000/requirements/risks \
  -H "Content-Type: application/json" \
  -d '{"markdown":"# Feature: Login\n## Acceptance Criteria\n- account locks after 5 failed attempts"}'
```
```json
{
  "feature": "Login",
  "user_story": "",
  "acceptance_criteria": ["account locks after 5 failed attempts"],
  "business_rules": [],
  "risks": ["Brute-force attacks against the login form"],
  "notes": []
}
```

### `POST /requirements/coverage`
Run the three-stage pipeline — **parse → extract business rules → analyze coverage** —
comparing the requirement against *retrieved* existing tests. **Requires a reachable LLM
provider and a populated retrieval index** (see §2; index tests via `/retrieval/index`
first). Makes two LLM calls (rule extraction + coverage) plus retrieval.

**Request body:** same as `/parse` — `{ "markdown": "..." }`.

**Response:** a `CoverageReport` (not a `Requirement`):
```json
{
  "covered": ["valid login is tested"],
  "gaps": ["account lockout after repeated failures is not tested"]
}
```

### `POST /requirements/generate`
The **orchestrator** — runs the entire pipeline in one call:
**parse → extract rules → analyze risks → retrieve → coverage → generate →
self-review**. **Requires a reachable LLM provider** (and, for useful coverage, a
populated retrieval index; see §2). Makes ~5 LLM calls.

**Request body:** same as `/parse` — `{ "markdown": "..." }`.

**Response:** a `GenerationResult` — the enriched requirement, the coverage report, and
the final reviewed test cases:
```json
{
  "requirement": { "feature": "Login", "business_rules": ["..."], "risks": ["..."], "...": "..." },
  "coverage": { "covered": ["..."], "gaps": ["..."] },
  "test_cases": [
    { "title": "Account locks after 5 failed logins", "type": "security",
      "priority": "high", "steps": ["..."], "expected_result": "...",
      "covers": "account lockout is not tested" }
  ]
}
```
Individual LLM stages **degrade gracefully**: a stage that fails records a note in
`requirement.notes` and the pipeline continues, so you get a best-effort result rather
than an error.

### `POST /retrieval/index`
Index (or upsert) existing test cases into the vector store for later search.
Requires a working retrieval backend (Chroma; see §2).

**Request body:**
```jsonc
{ "documents": [ { "id": "t1", "text": "...", "metadata": { "feature": "Login" } } ] }
```
`metadata` is optional. Response: `{ "indexed": <count> }`.

```bash
curl -X POST http://127.0.0.1:8000/retrieval/index \
  -H "Content-Type: application/json" \
  -d @examples/existing_tests.json:wrap   # wrap as {"documents": [...]} (see note)
```
> The sample file `examples/existing_tests.json` is a raw array; wrap it as
> `{"documents": [...]}` before posting.

### `POST /retrieval/search`
Return the indexed test cases most similar to a query (semantic search).

**Request body:**

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `query` | string | yes | Text to find similar test cases for |
| `k` | integer (1–50) | no (default 5) | Max results |

```bash
curl -X POST http://127.0.0.1:8000/retrieval/search \
  -H "Content-Type: application/json" \
  -d '{"query":"sign in using account credentials","k":3}'
```
```json
[
  {
    "id": "login-001",
    "text": "Verify a registered user can log in with a valid email and correct password.",
    "score": 0.62,
    "metadata": { "feature": "Login", "type": "positive" }
  }
]
```
Results are ordered best-first; `score` is normalized to 0..1 (higher = more similar).

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
| `business_rules` | string[] | `BusinessRuleExtractor` | filled by `/business-rules`; `[]` from `/parse` |
| `risks` | string[] | `RiskAnalyzer` | filled by `/risks`; `[]` from `/parse` |
| `notes` | string[] | parser | breadcrumbs (e.g. defaulted-feature note) |

The expected input Markdown shape and parsing rules are documented in the
[Milestone Walkthrough §3.2–3.3](./milestones.md).

### `CoverageReport` (response of `/requirements/coverage`)
| Field | Type | Notes |
| --- | --- | --- |
| `covered` | string[] | aspects already covered by existing tests |
| `gaps` | string[] | aspects not yet covered — the testing gaps to fill |

### `TestCase`
| Field | Type | Notes |
| --- | --- | --- |
| `title` | string | short name of the case |
| `type` | string | positive / negative / edge / security / … |
| `priority` | string | high / medium / low |
| `steps` | string[] | ordered steps to execute |
| `expected_result` | string | the assertion / expected outcome |
| `covers` | string | the rule / risk / gap this case addresses (traceability) |

### `GenerationResult` (response of `/requirements/generate`)
| Field | Type | Notes |
| --- | --- | --- |
| `requirement` | Requirement | the enriched requirement (rules + risks filled) |
| `coverage` | CoverageReport | the gap analysis |
| `test_cases` | TestCase[] | the final, self-reviewed cases |

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

The LLM-backed endpoints are tested with the **provider dependency overridden** by a
fake (`app.dependency_overrides[get_llm_provider]`), so the route, parser, agent, and
JSON validation all run for real while only the network call is faked — no model, key,
or cost. The real `OllamaProvider` has a smoke test that **auto-skips** when Ollama
isn't running. (API tests prove the *wiring*; the agents' unit tests prove the *logic*.)

---

## 9. File map

```
backend/app/
├── main.py              # FastAPI app + router wiring (composition root)
├── api/
│   ├── __init__.py      # exports the routers
│   ├── routes.py        # /parse, /business-rules, /risks, /coverage, /generate + DI
│   └── retrieval_routes.py  # /retrieval/index, /retrieval/search
├── services/
│   ├── requirement_parser.py   # RequirementParserService.parse()  (deterministic)
│   └── orchestrator.py         # GenerationOrchestrator — the full pipeline
├── agents/                      # LLM-backed agents
│   ├── json_support.py              # shared complete_json() helper (Rule of Three)
│   ├── business_rule_extractor.py   # BusinessRuleExtractor.extract()
│   ├── risk_analyzer.py             # RiskAnalyzer.analyze()
│   ├── coverage_analyzer.py         # CoverageAnalyzer.analyze() (LLM + retriever)
│   ├── test_generator.py            # TestGeneratorAgent.generate() (not yet wired to HTTP)
│   └── self_reviewer.py             # SelfReviewer.review() (not yet wired to HTTP)
├── providers/                   # LLM provider port + adapters (ADR-0002)
│   ├── base.py          # LLMProvider Protocol (the port)
│   ├── ollama_provider.py   # OllamaProvider adapter (httpx -> Ollama)
│   └── factory.py       # get_llm_provider() — selects backend from env
├── retrieval/                   # RAG retrieval layer (ADR-0003)
│   ├── base.py          # TestCaseRetriever port + document/result models
│   ├── chroma.py        # ChromaRetriever adapter (embedded ChromaDB)
│   ├── fake.py          # FakeRetriever (in-memory, tests)
│   └── factory.py       # get_retriever() — selects backend from env
└── models/
    ├── requirement.py   # Requirement (response model / domain entity)
    ├── coverage.py      # CoverageReport (coverage endpoint response)
    ├── test_case.py     # TestCase / TestSuite (generated output)
    └── generation.py    # GenerationResult (/generate response)
backend/tests/           # parser, api, agent, provider, retrieval tests
examples/existing_tests.json   # sample corpus to ingest via /retrieval/index
```

---

## 10. What's coming

The full backend pipeline is in place (through `POST /requirements/generate`), and a thin
**VS Code extension** (in `extension/`) already calls it (ADR-0005). What remains builds
on the same patterns:

- Additional provider adapters (Claude, OpenAI) — each a new `complete()` behind the
  same port. See [ADR-0002](./adr/0002-pluggable-llm-provider.md).
- Richer extension UX (a webview; an ingest command for `/retrieval/index`) and CI.
