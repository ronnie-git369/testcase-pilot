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

## Project progress — ~22% complete

> An **effort-weighted** estimate (not a feature count). Checked items are built and
> tested; the remaining items are individually heavier — RAG, test generation, and the
> VS Code extension are the big ones.

| # | Component | Status | ~Weight |
| --- | --- | --- | --- |
| 1 | Foundation + architecture docs (M1–M2) | ✅ done | 10% |
| 2 | `Requirement` model + parser, tested (M3) | ✅ done | 8% |
| 3 | `POST /requirements/parse` endpoint (M4 · Step 1) | ✅ done | 4% |
| 4 | Pluggable LLM provider (OpenAI / Claude / Ollama — ADR-0002) | ⬜ next | 8% |
| 5 | `BusinessRuleExtractor` agent | ⬜ | 6% |
| 6 | `RiskAnalyzer` agent | ⬜ | 6% |
| 7 | RAG over existing tests (ChromaDB — ADR-0003) | ⬜ | 12% |
| 8 | Coverage-gap detection | ⬜ | 8% |
| 9 | `TestGeneratorAgent` (manual + Playwright cases) | ⬜ | 12% |
| 10 | Self-review / critique step | ⬜ | 6% |
| 11 | Orchestrator pipeline + `POST /generate` (ADR-0004) | ⬜ | 8% |
| 12 | VS Code extension (thin TypeScript client — ADR-0005) | ⬜ | 10% |
| 13 | Examples, golden cases, prompts, polish | ◐ started | 2% |

**Done so far: items 1–3 ≈ 22%.**

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

## Milestone 4 — Exposing the Parser over HTTP

> **Status:** In progress. Step 1 (the parse endpoint, below) is complete and tested.
> Step 2 — the first LLM-backed agent (`BusinessRuleExtractor`) — is next.

**Goal (Step 1):** expose `RequirementParserService` over a real HTTP endpoint so the
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

---

## What's next (Milestone 4 · Step 2 and beyond)

- **`BusinessRuleExtractor`** — the first LLM-backed agent. Introduces the pluggable
  provider (ADR-0002, via the `claude-api` integration) and fills
  `Requirement.business_rules`. This is the first step across the deterministic →
  probabilistic line.
- Then: `RiskAnalyzer`, RAG over existing tests (ChromaDB, ADR-0003), coverage-gap
  detection, the `TestGeneratorAgent`, and the orchestrator (`POST /generate`,
  ADR-0004).

Open question still parked: should `feature` get a `min_length=1` constraint on the
model, or should that validation live in a separate layer? (See §3.4.)
