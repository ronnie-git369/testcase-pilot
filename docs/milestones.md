# TestCasePilot — Milestone Walkthrough (M1–M4)

> A review-oriented narrative of how TestCasePilot has been built so far, and *why*
> each decision was made. Milestones 1–2 cover the foundation and design; Milestone 3
> is the first real engine; Milestone 4 exposes it over HTTP. Milestones 3–4 are
> documented in depth.
>
> Companion docs: [Architecture](./architecture.md) · [ADRs](./adr/README.md) ·
> [Diagrams](./diagrams/README.md) · [Product Requirements](./product-requirements.md)

---

## How to read this document

The build follows one guiding rule that you'll see repeated everywhere:

> **Push everything you *can* make deterministic out of the LLM.**

A reliable, testable, deterministic spine is built first; the probabilistic
(LLM-backed) agents will hang off it later. Milestone 3 is the first vertebra of that
spine, and Milestone 4 puts an HTTP face on it — both still fully deterministic.

```
        DETERMINISTIC ZONE                  │       PROBABILISTIC ZONE (later)
                                            │
   raw markdown                             │
        │                                   │
        ▼                                   │
  ┌────────────────────┐   Requirement      │   ┌──────────────────────┐
  │ RequirementParser  │ ─────────────────► │   │ BusinessRuleExtractor │ (LLM)
  │ Service.parse()    │   (structured)     │   │ RiskAnalyzer          │ (LLM)
  │  • no LLM, no I/O    │                   │   │ TestGeneratorAgent    │ (LLM)
  │  • same in ⇒ same out│                   │   └──────────────────────┘
  └────────────────────┘                    │      same in ⇒ maybe different out
   built in Milestone 3                      │      future milestones
```

---

## Project progress — ~88% complete

> An **effort-weighted** estimate (not a feature count). Checked items are built and
> tested; the remaining items are individually heavier — RAG, test generation, and the
> VS Code extension are the big ones.

| # | Component | Status | ~Weight |
| --- | --- | --- | --- |
| 1 | Foundation + architecture docs (M1–M2) | ✅ done | 10% |
| 2 | `Requirement` model + parser, tested (M3) | ✅ done | 8% |
| 3 | `POST /requirements/parse` endpoint (M4 · Step 1) | ✅ done | 4% |
| 4 | Pluggable LLM provider port + Ollama adapter (ADR-0002) | ✅ done | 8% |
| 5 | `BusinessRuleExtractor` agent + `/business-rules` endpoint | ✅ done | 6% |
| 6 | `RiskAnalyzer` agent + `/risks` endpoint | ✅ done | 6% |
| 7 | RAG retrieval over existing tests (ChromaDB — ADR-0003) | ✅ done | 12% |
| 8 | Coverage-gap detection (`CoverageAnalyzer` + `/coverage`) | ✅ done | 8% |
| 9 | `TestGeneratorAgent` (manual cases) | ✅ done | 12% |
| 10 | Self-review / critique step (`SelfReviewer`) | ✅ done | 6% |
| 11 | Orchestrator pipeline + `POST /requirements/generate` (ADR-0004) | ✅ done | 8% |
| 12 | VS Code extension (thin TypeScript client — ADR-0005) | ⬜ next | 10% |
| 13 | Examples, golden cases, prompts, polish | ◐ started | 2% |

**Done so far: items 1–11 ≈ 88%.**

Two caveats:
- *Effort-weighted, not feature-count.* By count it's 3 of ~13 (~23%), but the remaining
  items are individually harder, so wall-clock progress may feel lower than 22%.
- *The deterministic foundation is disproportionately valuable.* The model, the tested
  service pattern, the API/DI conventions, and the test harness are reused by every
  future agent — you've built the part everything else stands on.

---

## Milestone 1 — Project Foundation

**Goal:** a runnable, version-controlled FastAPI service skeleton.

**What was established** (git commits `1e69e3d`, `d19566d`):

- Git + GitHub repository, `.gitignore`, `LICENSE`, initial `README.md`.
- Python virtual environment at `backend/.venv` (Python 3.9+).
- FastAPI entrypoint `backend/app/main.py`, imported as `app.main:app`, serving:
  - `GET /` — a service banner.
  - `GET /health` — a health check.
- **Fully pinned** dependencies in `backend/requirements.txt` (including transitive
  deps) for reproducible builds.
- The `app` package created (`backend/app/__init__.py`).

**Why it matters:** before any features, you want a service that *starts*, a way to run
it, and reproducible dependencies. Pinning everything (not just top-level packages)
means a checkout today and a checkout in six months install byte-identical environments.

**Run it:**

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload     # http://127.0.0.1:8000  (docs at /docs)
```

---

## Milestone 2 — Architecture & Design Documentation

**Goal:** decide *what* we're building and *why* before writing feature code.

**What was established** (git commits `c1e238a`, `730a065`):

- `docs/architecture.md` — the living system-architecture document (vision, users,
  workflow, components).
- `docs/product-requirements.md` — the product requirements.
- `docs/adr/0001..0005` — **Architecture Decision Records** capturing the load-bearing
  choices:
  | ADR | Decision |
  | --- | --- |
  | 0001 | Use FastAPI for the backend |
  | 0002 | Pluggable LLM provider (OpenAI / Claude / Ollama) |
  | 0003 | RAG over existing tests with ChromaDB |
  | 0004 | Agent orchestration pipeline (analyze → … → self-review) |
  | 0005 | VS Code extension as a thin client |
- `docs/diagrams/` — system context, agent pipeline, and request-sequence diagrams.
- `docs/git-commit-guide.md` and `CLAUDE.md` (guidance for contributors / AI agents).
- Empty **placeholder** packages were laid out for the planned structure
  (`app/api/`, `app/agents/`, `app/models/`, `app/services/`).

**Why it matters:** ADRs record *why* a decision was made so that future-you (or a new
teammate) doesn't re-litigate it or accidentally undo it. The architecture here is
**intent** — most of it is not built yet. Milestone 3 is where intent becomes code.

---

## Milestone 3 — Requirement Analysis Engine

**Goal:** convert a Markdown requirement into a structured `Requirement` object —
*nothing more*.

This milestone has exactly **one responsibility**: text → structure. By design it does
**not** generate test cases, perform risk analysis, call an LLM, search RAG, or export
files. That discipline (the Single Responsibility Principle) is what later lets the
parser become one clean, callable *tool* for the agent orchestrator.

### 3.1 The `Requirement` model — the central contract

File: `backend/app/models/requirement.py`

```python
class Requirement(BaseModel):
    feature: str = Field(...)                                  # required
    user_story: str = Field(default="")
    acceptance_criteria: list[str] = Field(default_factory=list)
    business_rules: list[str]      = Field(default_factory=list)   # filled later
    risks: list[str]               = Field(default_factory=list)   # filled later
    notes: list[str]               = Field(default_factory=list)   # parser breadcrumbs
```

| Field | Filled by | Why it exists |
| --- | --- | --- |
| `feature` | parser (now) | The anchor; test cases are grouped by feature. **Required** — a requirement with no feature isn't valid. |
| `user_story` | parser (now) | The narrative intent ("as a… I want… so that…"). |
| `acceptance_criteria` | parser (now) | The testable conditions — raw material for test generation. |
| `business_rules` | `BusinessRuleExtractor` (future) | Domain constraints. Empty now, but the field exists so the contract is stable. |
| `risks` | `RiskAnalyzer` (future) | Risk areas to prioritize coverage. Empty now. |
| `notes` | any stage | Escape hatch / breadcrumbs so information is never silently lost. |

**Why structured data beats plain text:** you can't `assert len(req.acceptance_criteria)`
against a paragraph of Markdown. Structure gives addressability, validation,
testability, and a stable contract every future agent depends on.

Two Python details worth knowing:
- `Field(...)` (the Ellipsis) marks a field **required**; Pydantic raises
  `ValidationError` if it's missing.
- `default_factory=list` gives each instance its **own** list — avoiding Python's
  classic *mutable default argument* bug (never write `= []` as a default).

### 3.2 The input contract

The parser commits to this Markdown shape:

```markdown
# Feature: User Login

## User Story
As a registered user, I want to log in with my email and password
so that I can access my account.

## Acceptance Criteria
- Valid credentials grant access to the dashboard
- An invalid password shows an error message
- The account locks after 5 consecutive failed attempts
```

Mapping rules:
- `# Feature: X` (or plain `# X`) H1 → `feature` (the `Feature:` label is stripped).
- `## User Story` section → `user_story` (lines joined into one statement).
- `## Acceptance Criteria` section → `acceptance_criteria` (each `-`/`*` bullet).
- `business_rules` / `risks` → **always left empty** (future agents' job).
- Heading matching is **case-insensitive and whitespace-trimmed**.

### 3.3 The parser — a single-pass state machine

File: `backend/app/services/requirement_parser.py`

The public API is one method:

```python
RequirementParserService().parse(markdown: str) -> Requirement
```

Internally it makes **one pass** over the document (`_tokenize`) into a feature name
plus a `{heading: [content lines]}` map; small readers then build each field. The
"state" is simply *which section are we currently inside?*

```
                  ┌──────────────────────────────────────────────┐
   "## <heading>" │                          line is "# ..."      │
        ┌─────────▼─────────┐   (other "##")   ┌─────────────────┴┐
        │  INSIDE a section  │ ───────────────► │  OUTSIDE          │
        │  (collect lines)   │                  │  (ignore content) │
        └─────────▲─────────┘                  └──────────┬────────┘
                  │            "## <known heading>"        │
                  └────────────────────────────────────────┘

   H1 line             → set feature (first non-empty wins), close section
   H2 line             → open that section
   content + INSIDE    → append to that section's lines
   content + OUTSIDE   → ignore
   blank line          → skip
```

**Complexity:** `O(n)` in document size — one pass, each line touched once. You can't do
better; every character must be read at least once.

**Why a hand-rolled scanner (not a Markdown library)?** Zero new runtime dependencies,
full control, trivial to unit-test, and the input format is one we fully define. The
logic was first written as separate per-field scans; once heading detection appeared in
a *third* place (the Rule of Three), the duplication had *earned* the refactor into the
single `_tokenize` pass — abstraction driven by evidence, not speculation.

### 3.4 Key design decisions

| Decision | Choice | Rationale |
| --- | --- | --- |
| Missing feature | Default to `"Untitled"` **and** add a `notes` breadcrumb | **Permissive but observable.** Batch jobs never crash, but a malformed requirement is *visible*, never silently corrupted — the failure mode a QA engineer fears most. |
| `feature` validation | Required, but **not** `min_length`-checked | Keep the model a permissive container; defer "is this a *good* feature?" judgment to a validation layer later. (Open question for M4.) |
| `business_rules` / `risks` | Never filled by the parser | Single Responsibility — those are future probabilistic agents' jobs; the parser stays purely deterministic. |
| Heading match | Case-insensitive + trimmed | Forgiving against human-written docs without "magic" synonym guessing. |
| Build style | Vertical slices + TDD | Each increment is a complete, tested parser that simply understands less of the document. |

### 3.5 Edge cases the parser handles (each is a test)

| Input situation | Behavior |
| --- | --- |
| No feature heading / empty input | `feature="Untitled"` + breadcrumb note |
| `# Feature:` with no name | Treated as missing (present ≠ meaningful) |
| Only an `## H2` present | Not mistaken for the feature |
| `## user story` (lower-case) | Matched (case-insensitive) |
| Multi-line user story + blank lines | Joined into one clean statement |
| Content after the next heading | Excluded — the section self-closes |
| Mixed `-` and `*` bullets | Both accepted |
| Stray prose / empty bullets under criteria | Ignored |
| Repeated `## Acceptance Criteria` blocks | Merged into one list |

### 3.6 Tests — 26 total, all green

| File | Count | Covers |
| --- | --- | --- |
| `backend/tests/test_requirement.py` | 4 | Model contract: required field, empty defaults, per-instance list isolation, full round-trip |
| `backend/tests/test_requirement_parser.py` | 22 | Feature extraction (8), user-story section (6), acceptance criteria + full document (8) |

Each test docstring names the **bug it prevents** — the tests double as documentation.

**Run the tests** (from inside `backend/`):

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt   # first time only (pytest etc.)
pytest                                # config is in pyproject.toml
```

### 3.7 Tooling decisions introduced in M3

- `backend/tests/` — tests live beside the backend, **outside** the shipped `app`
  package.
- `backend/pyproject.toml` — pytest config: `testpaths=["tests"]`, `pythonpath=["."]`
  (so `from app… import` resolves with no `PYTHONPATH` hacks), `addopts="-v"`.
- `backend/requirements-dev.txt` — dev/test deps (pinned), separate from runtime
  `requirements.txt`, because pytest is never imported by `app/` and shouldn't ship to
  production. (This refines CLAUDE.md's "all deps in requirements.txt" note.)

### 3.8 How this becomes the Agentic system

`parse(md) -> Requirement` is already **tool-shaped**: typed in, typed out, no side
effects. When the orchestrator is built, step 1 is literally:

```python
requirement = RequirementParserService().parse(raw_markdown)
```

…and the resulting `Requirement` is the shared object every later agent reads from and
writes to:

```
parse() ──► Requirement ──► BusinessRuleExtractor  → fills business_rules
                        ├──► RiskAnalyzer           → fills risks
                        ├──► CoverageAnalyzer + RAG → compares vs existing tests
                        └──► TestGeneratorAgent     → produces test cases
```

The empty `business_rules` / `risks` fields aren't oversights — they're the **seats**
waiting for those agents.

---

## Milestone 4 — HTTP API & First LLM Agent

> **Status:** Step 1 (parse endpoint) and Step 2 (LLM-backed `BusinessRuleExtractor`
> + `/business-rules` endpoint) are complete and tested.

### Step 1 — Expose the parser over HTTP

**Goal:** expose `RequirementParserService` over a real HTTP endpoint so the
VS Code thin client (ADR-0005) has something to call — while staying fully
deterministic. This is the first **client-facing entry point**, and the
request/response pattern set here is the same one the future `POST /generate`
(orchestrator) will follow.

### 4.1 The endpoint

`POST /requirements/parse` — file `app/api/routes.py`, mounted in `app/main.py`.

- **Request body (JSON):** `{ "markdown": "<raw markdown>" }` — a Pydantic DTO
  (`ParseRequirementRequest`).
- **Response body:** the `Requirement` directly (via `response_model=Requirement`).
- **Empty / whitespace Markdown:** returns **200** with the permissively-defaulted
  Requirement (`feature="Untitled"` + a `notes` breadcrumb) — consistent with the
  parser, not a 422.
- **Missing `markdown` field:** **422** (FastAPI request validation at the boundary).

```
POST /requirements/parse
{ "markdown": "# Feature: Checkout\n## Acceptance Criteria\n- card payment succeeds" }

200 OK
{ "feature": "Checkout", "user_story": "",
  "acceptance_criteria": ["card payment succeeds"],
  "business_rules": [], "risks": [], "notes": [] }
```

### 4.2 Clean Architecture layering

The dependency arrow points **inward**: HTTP → route → service → model. No inner layer
knows about the outer ones.

```
 FastAPI / Uvicorn  (frameworks / drivers)
   └─ app/api/routes.py          THIN adapter: HTTP <-> domain, no logic
        └─ RequirementParserService    application logic
             └─ Requirement             domain entity
```

Key choices:
- **`main.py` is a composition root** — it only `include_router(...)`; it holds no
  route logic.
- **The service is injected** via FastAPI `Depends(get_parser)`, not constructed inside
  the handler. This makes the route testable (override via `app.dependency_overrides`)
  and is exactly where a configured, provider-aware instance will be wired in later
  (ADR-0002) — it rehearses how the orchestrator will receive its LLM provider.
- **DTO vs entity:** `ParseRequirementRequest` (an HTTP input shape) lives in the API
  layer; `Requirement` (a domain entity) stays in `models/`. Different layers, different
  reasons to change.
- **`response_model=Requirement`** serializes the model, *filters* output to exactly its
  fields, and publishes the schema to `/docs`.

### 4.3 Tests — 3 API tests (29 total, all green)

`backend/tests/test_api.py` uses FastAPI's `TestClient` to exercise the full HTTP stack
(routing, validation, serialization):

| Test | Asserts |
| --- | --- |
| structured response | well-formed doc → 200 with every field populated |
| permissive empty | empty markdown → 200 with `Untitled` + breadcrumb |
| required field | missing `markdown` → 422 |

API tests prove the **wiring**; the M3 unit tests prove the **logic** — different
layers, different tests.

### 4.4 A dependency lesson

`TestClient` needs `httpx`. Adding it surfaced a pre-existing gap: `anyio` was installed
but its `sniffio` dependency was missing *and* unlisted — so the "fully pinned" claim
wasn't actually true for transitive deps. Fixed by pinning `httpx`, `httpcore`,
`certifi`, and `sniffio` in `requirements-dev.txt`. **Takeaway:** "fully pinned" only
holds if it includes the *transitive* deps; environments drift when a transitive dep is
satisfied-but-unlisted.

### Try it

```bash
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload      # open http://127.0.0.1:8000/docs
```

### Step 2 — First LLM-backed agent (`BusinessRuleExtractor`)

**Goal:** cross from the deterministic spine into the probabilistic zone — infer a
requirement's **business rules** with a local LLM — while keeping the code
vendor-agnostic and testable offline.

#### Port & Adapter (Hexagonal) architecture

Agents depend on an abstraction *we* own, never on a vendor SDK (ADR-0002):

```
  BusinessRuleExtractor ──► LLMProvider (PORT)  .complete(prompt) -> str
                                  ▲      ▲       ▲
                          OllamaProvider │   (Claude / OpenAI later)
                                         │
                                   FakeProvider (tests)
```

#### Components

| File | Role |
| --- | --- |
| `app/providers/base.py` | `LLMProvider` — a `typing.Protocol` port: `complete(prompt) -> str` |
| `app/providers/ollama_provider.py` | `OllamaProvider` adapter — calls Ollama's `/api/generate` via `httpx`; env `OLLAMA_HOST` / `OLLAMA_MODEL`; failures wrapped in `OllamaError` |
| `app/providers/factory.py` | `get_llm_provider()` — selects the backend from `LLM_PROVIDER` (default `ollama`) |
| `app/agents/business_rule_extractor.py` | `BusinessRuleExtractor.extract(req) -> list[str]` |

#### Taming non-deterministic output

`extract()` turns messy LLM text into a validated `list[str]`:
1. **Prompt for JSON** of an exact shape (`{"business_rules": [...]}`), with an
   explicit empty case.
2. **Extract** the object from first `{` to last `}` — tolerates prose / ```json fences.
3. **Validate** with a Pydantic schema (wrong key/type → `ValidationError`).
4. **Retry once**; on persistent failure raise `BusinessRuleExtractionError` (never
   silently return `[]`, which would masquerade as "no rules").

The agent returns the rules; it does **not** mutate the `Requirement` (pure, composable).

#### The endpoint — a baby orchestrator

`POST /requirements/business-rules` (body `{ "markdown": "..." }`) composes the first
two pipeline stages:

```python
requirement = parser.parse(request.markdown)                  # deterministic
requirement.business_rules = extractor.extract(requirement)   # probabilistic
return requirement
```

The provider is injected via `Depends(get_llm_provider)`. Tests override that **leaf**
dependency with a fake — so the route, parser, extractor, and JSON validation all run
for real while only the network call is faked.

#### Testing probabilistic code, deterministically

| Test file | What it proves |
| --- | --- |
| `tests/test_business_rule_extractor.py` (7) | prompt building, JSON extraction, validation, retry, error — via `FakeProvider`, offline |
| `tests/test_business_rules_api.py` (2) | the endpoint end-to-end with the provider overridden |
| `tests/test_ollama_provider.py` (1) | live smoke test — **auto-skips** when Ollama isn't running |

Suite total: **38 passed, 1 skipped**. `httpx` was promoted from a dev-only dep to a
runtime dep (the adapter uses it), so it now lives in `requirements.txt`.

#### Run it for real (optional)

```bash
ollama pull llama3.1 && ollama serve      # terminal 1
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload             # terminal 2 → POST to /requirements/business-rules
```

---

## Milestone 5 — Risk Analysis & RAG Retrieval

### Risk analysis (item #6) — `RiskAnalyzer`

The second LLM agent, built as a deliberate near-clone of `BusinessRuleExtractor`:
same `LLMProvider` port and the same prompt → extract-JSON → Pydantic-validate →
retry-once pattern.

- `RiskAnalyzer.analyze(req) -> list[str]` — pure (returns risks, does not mutate the
  Requirement). Its prompt includes `business_rules` when present, so risks sharpen if
  run after rule extraction.
- Endpoint `POST /requirements/risks` (parse → analyze), provider injected via `Depends`.
- **Rule of Three:** the duplication with `BusinessRuleExtractor` is intentional — a
  *third* JSON-agent will justify extracting a shared base, not the second.

### RAG retrieval (item #7) — the "R" in RAG

**Goal:** give the system *memory of existing tests* so later steps can reason about
what's already covered. Built deterministic and offline-testable.

**Concepts:** an **embedding** turns text into a vector where similar meaning → nearby
vectors; a **vector store** (ChromaDB) answers "give me the k nearest." Two phases:
**ingest** existing tests once, **retrieve** the top-k per request.

**Architecture (port & adapter):**

| File | Role |
| --- | --- |
| `app/retrieval/base.py` | `TestCaseRetriever` Protocol (port) + `TestCaseDocument` / `RetrievedTestCase` models |
| `app/retrieval/chroma.py` | `ChromaRetriever` — embedded ChromaDB, default local ONNX embedding, persists to `CHROMA_PATH` |
| `app/retrieval/fake.py` | `FakeRetriever` — in-memory Jaccard scoring for offline tests |
| `app/retrieval/factory.py` | `get_retriever()` — selects backend from `RETRIEVER` (cached) |

**Endpoints (separate `/retrieval` router):** `POST /retrieval/index`,
`POST /retrieval/search`. The retriever is injected; tests override it with a shared
`FakeRetriever` so index→search round-trips with no ChromaDB.

**The payoff:** the integration test queries *"sign in using account credentials"* and
retrieves the *"user logs in with a valid email and password"* test — **no shared
keywords**, matched on meaning. That's semantic search, the whole point of embeddings.

**Dependency note:** `chromadb` pulled ~60 transitive packages, so `requirements.txt`
was regenerated as a full pinned lockfile (the pytest stack stays in
`requirements-dev.txt`). `pip-tools` is the scalable path once a tree gets this big.
The `.chroma/` store is generated data and is git-ignored.

**Tests:** `FakeRetriever` unit tests + `/retrieval` endpoint tests (offline) + a
skip-guarded `ChromaRetriever` integration test. Suite: **54 passed, 1 skipped**.

---

## Milestone 6 — Coverage-Gap Detection (item #8)

The core of TestCasePilot's "depth over volume" value, and two architecture firsts.

### The Rule-of-Three refactor (finally triggered)

With a *third* JSON-emitting agent on the way, the duplicated
prompt → extract-JSON → validate → retry loop earned a shared home:

- `app/agents/json_support.py` — `complete_json(provider, prompt, schema, *, error_type)`.
  Each agent now supplies only what *varies* (its prompt, Pydantic schema, and domain
  error); the constant parse/retry loop lives once.
- `BusinessRuleExtractor` and `RiskAnalyzer` were rebuilt on it with **zero test
  changes** — the 54 existing tests were the safety net. `error_type` as a parameter is
  what let each agent keep its own exception.

### `CoverageAnalyzer` — the first dual-port agent

Depends on **both** `LLMProvider` and `TestCaseRetriever`:

```
   Requirement ──► CoverageAnalyzer ──► CoverageReport { covered, gaps }
                      │            │
                      ▼            ▼
            TestCaseRetriever    LLMProvider
            (retrieve existing)  (reason about gaps)
```

`analyze(req)` searches **per acceptance criterion and business rule**, dedupes hits by
id, then makes one `complete_json` call over the requirement + retrieved tests. Pure
(returns a `CoverageReport`, mutates nothing). Both deps injected → tests run offline
with a `FakeProvider` + a stub retriever.

### Endpoint — the closest thing yet to the orchestrator

`POST /requirements/coverage` chains **parse → extract business rules → analyze
coverage** and returns a `CoverageReport`. FastAPI caches `get_llm_provider` within a
request, so the extractor and analyzer share one provider instance (the endpoint test
exploits this with a *sequenced* fake: first completion = rules, second = coverage).

Tests: 6 `CoverageAnalyzer` unit tests + 2 endpoint tests. Suite: **62 passed, 1
skipped**.

---

## Milestone 7 — Test Generation (item #9)

The payoff: `TestGeneratorAgent` turns the analysis into review-ready test cases.

- **Models** (`app/models/test_case.py`): `TestCase { title, type, priority, steps,
  expected_result, covers }` + `TestSuite { cases }`. `covers` ties each case to the
  rule / risk / gap it addresses — the traceability a QA lead signs off on.
- **Agent** (`app/agents/test_generator.py`): `generate(requirement, gaps=None) ->
  list[TestCase]`. The *fourth* agent on `complete_json` — **zero** new parsing code;
  only a new prompt + schema. Prompt carries gaps + rules + risks and is told to favor
  depth over volume and not re-test what's covered. Pure; drops incomplete cases.
- **Design notes:** `type`/`priority` are `str` (constrained by the prompt, not the
  schema) so an odd LLM value is data to inspect, not a hard `ValidationError`.
  "Playwright" output was deferred — runnable automation needs the app's selectors/URLs,
  which the backend doesn't have; manual cases are the accurate, high-value output now.
- **No endpoint yet** — generation is wired into the `POST /generate` orchestrator (#11).

Tests: 5 offline unit tests (FakeProvider). Suite: **67 passed, 1 skipped**.

---

## Milestone 8 — Self-Review (item #10)

The "reviews its own output before presenting" step from the vision.

- `app/agents/self_reviewer.py`: `SelfReviewer.review(requirement, cases) ->
  list[TestCase]`. The *fifth* agent on `complete_json` (schema reused: `TestSuite`).
- It serializes the **draft cases into the prompt** and asks the model to critique them
  (duplicate/overlapping cases, missing negative/edge cases, vague steps, weak
  assertions), then return an **improved** set.
- Pure; drops incomplete cases; **skips the LLM entirely when given no cases** (don't
  waste a call). Same `(req, cases) -> list[TestCase]` contract as the generator, so the
  orchestrator can chain `generate → review` directly.

Tests: 5 offline unit tests. Suite: **72 passed, 1 skipped**.

---

## Milestone 9 — The Orchestrator (item #11)

The capstone: one call runs the whole pipeline and returns review-ready test cases.

- `app/services/orchestrator.py`: `GenerationOrchestrator` (an application service —
  orchestration is logic, not routing). It is given its six collaborators (parser +
  five agents) via constructor injection and chains them:
  **parse → rules → risk → coverage → generate(gaps) → self-review**.
- **Graceful degradation:** each LLM stage is wrapped; on its domain error the pipeline
  records a note on `requirement.notes` and continues with a default — so one flaky
  stage never 500s the whole request (the "permissive but observable" principle again).
  Provider/connectivity errors are *not* swallowed.
- `app/models/generation.py`: `GenerationResult { requirement, coverage, test_cases }`.
  The requirement + coverage double as the *rationale* for the generated cases.
- **Endpoint `POST /requirements/generate`** (`app/api/routes.py`): thin — builds the
  orchestrator from injected collaborators and calls `run`. Because FastAPI caches
  `get_llm_provider` within a request, all five agents share one provider instance.

**Tests:** 2 orchestrator unit tests (real parser + stub agents: chaining + graceful
degradation) and a full-pipeline endpoint test using a *sequenced* fake provider (one
response per stage). Suite: **76 passed, 1 skipped**.

---

## What's next

- **VS Code extension (item #12):** the thin TypeScript client (ADR-0005) that POSTs a
  requirement to `/requirements/generate` and renders the review-ready cases — the last
  backend-side milestone before the product is end-to-end usable.
- Additional provider adapters: a **Claude** adapter (`claude-api` skill) and **OpenAI**,
  each just a new `complete()` behind the same port.

Open question still parked: should `feature` get a `min_length=1` constraint on the
model, or should that validation live in a separate layer? (See §3.4.)

Open question still parked: should `feature` get a `min_length=1` constraint on the
model, or should that validation live in a separate layer? (See §3.4.)
