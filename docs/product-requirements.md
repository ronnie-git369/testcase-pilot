# TestCasePilot — Product Requirements Document (PRD)

> Status: Draft v0.1 · Last updated 2026-06-29 · Owner: Product
> Companion docs: [Architecture](./architecture.md) · [ADRs](./adr/README.md)

---

## 1. Summary

TestCasePilot is an agentic AI QA assistant that converts software requirements into
review-ready, enterprise-quality test cases. It runs inside the engineer's editor (VS
Code) and reasons like a senior QA engineer — analyzing intent, extracting business
rules, assessing risk, mining existing coverage via RAG, and self-reviewing — to produce
*fewer, higher-signal* cases instead of a shallow generated list.

## 2. Problem Statement

Turning requirements into test cases is slow, repetitive, and uneven in quality:

- Engineers spend hours restating acceptance criteria and enumerating obvious paths.
- The high-value work — edge cases, business-rule reasoning, finding gaps in existing
  coverage — gets squeezed out by the mechanical work.
- Generic LLM "generate tests" tools produce high *volume, low signal* output that adds
  review burden instead of removing it, and ignore the team's existing test corpus.

## 3. Goals & Non-Goals

### Goals
- Produce review-ready test cases a QA lead would sign off on, with rationale.
- Optimize for **depth over volume** — minimize redundant / low-value cases.
- Ground generation in the team's **existing** test cases (RAG) and surface **coverage gaps**.
- Keep the LLM provider **pluggable** (cost / latency / data-residency choice).
- Meet engineers in their editor with a low-friction workflow.

### Non-Goals (for MVP)
- Executing tests or generating automation code/scripts.
- Replacing a test-management system (TestRail/Xray/etc.) — we integrate later, not replace.
- Multi-tenant SaaS hosting, billing, or org-level admin.
- Fine-tuning or training custom models.

## 4. Target Users & Personas

| Persona | Primary need | Success looks like |
| --- | --- | --- |
| **QA Engineer** (primary) | Fast, thorough cases from a requirement | Accepts most cases with light edits; catches edge cases they'd have missed |
| **QA Lead** | Trustworthy, reviewable output + gap visibility | Spends review time on judgment, not triage of noise |
| **SDET / Engineer** | In-editor generation consistent with team style | Generates cases without leaving VS Code |
| **PM / BA** (secondary) | Early signal on untestable requirements | Ambiguities flagged before dev starts |

## 5. User Stories

- *As a QA engineer*, I can send a selected requirement from VS Code and get back
  structured test cases so I don't hand-write the obvious ones.
- *As a QA engineer*, I can see **why** each case exists (rule / risk / gap) so I can
  trust and defend the coverage.
- *As a QA lead*, I can see which cases fill **gaps** vs. duplicate existing coverage so I
  review efficiently.
- *As an SDET*, I can pick the **LLM provider** (cloud or local Ollama) to fit cost and
  data-residency constraints.
- *As a PM*, I get flagged when a requirement is **ambiguous or untestable** (future).

## 6. Functional Requirements

### MVP (must-have)

| ID | Requirement | Acceptance criteria |
| --- | --- | --- |
| FR-1 | Generate test cases from a single requirement | `POST /generate` accepts requirement text, returns structured cases |
| FR-2 | Multi-step agent pipeline | Pipeline runs analyze → extract → risk → retrieve → gap → generate → self-review |
| FR-3 | Pluggable LLM provider | Provider selected via env (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `OLLAMA_HOST`); no hard-coded provider |
| FR-4 | RAG over existing test cases | Retrieval step queries ChromaDB; generation conditioned on retrieved cases |
| FR-5 | Coverage-gap signal | Output distinguishes new-coverage cases from ones overlapping existing tests |
| FR-6 | Structured, typed output | Responses validated by Pydantic v2; each case has steps, expected result, rationale, priority |
| FR-7 | Traceability | Each case references the rule / risk / gap it addresses |
| FR-8 | VS Code extension | Send requirement, render cases, copy/export accepted cases |
| FR-9 | Health & docs | `GET /health` returns healthy; OpenAPI docs at `/docs` |

### Future (should/could-have)

| ID | Requirement |
| --- | --- |
| FR-10 | Batch / bulk requirement processing |
| FR-11 | Two-way sync with Jira/Xray, TestRail, Azure Test Plans |
| FR-12 | Coverage dashboard across a module/release |
| FR-13 | Requirement quality linting (ambiguous / untestable detection) |
| FR-14 | Feedback loop: accept/reject signals tune retrieval & prompts |
| FR-15 | Localization of generated cases |

## 7. Non-Functional Requirements

- **Quality:** generated cases should be review-ready; target ≥70% acceptance with only
  minor edits in pilot use.
- **Performance:** single-requirement generation returns within ~30s on a cloud provider
  (target; pipeline depth dominates latency).
- **Configurability:** switching providers requires only env changes, no code edits.
- **Security:** secrets only in git-ignored `backend/.env`; no credentials in source or logs.
- **Privacy / data residency:** local Ollama path supports keeping requirements on-prem.
- **Portability:** Python 3.9+; dependencies fully pinned (incl. transitive).
- **Observability:** health endpoint + structured logs for pipeline steps (MVP-light).

## 8. Success Metrics

| Metric | Target (pilot) |
| --- | --- |
| Test-case acceptance rate (accepted with ≤minor edits) | ≥ 70% |
| Redundant cases per session (overlap with existing) | < 15% of generated |
| Time-to-first-cases for a requirement | < 1 min wall-clock |
| Edge cases surfaced that the engineer hadn't listed | ≥ 1 per requirement (qualitative) |

## 9. Assumptions & Dependencies

- The team has an existing corpus of test cases worth ingesting for RAG.
- Users have access to at least one LLM provider (API key or local Ollama).
- VS Code is the primary editor for the target audience.
- Backend is the single service; the extension stays thin.

## 10. Risks & Open Questions

| Risk / question | Mitigation / note |
| --- | --- |
| LLM output quality varies by provider | Pluggable providers + self-review step; evaluate per provider |
| RAG corpus quality/coverage unknown | Provide ingestion tooling; measure overlap metrics |
| Latency from multi-step pipeline | Allow step toggles; cache analysis; stream partial results (future) |
| Cost of cloud LLM calls | Ollama local path; prompt/token budgeting |
| How are cases exported to test-mgmt tools? | Out of MVP scope; clipboard/file first, integrations in Phase 4 |

## 11. Release Plan

Aligned with the [Architecture roadmap](./architecture.md#project-roadmap): Phase 1 MVP
backend (`/generate` + pipeline + provider + RAG-light) → Phase 2 full RAG & coverage →
Phase 3 VS Code client + examples + tests → Phase 4 integrations & dashboard.
