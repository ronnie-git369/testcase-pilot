# ADR-0004: Multi-step agent orchestration pipeline

- **Status:** Accepted
- **Date:** 2026-06-29
- **Deciders:** Engineering

## Context

The product thesis is **depth over volume**: fewer, higher-signal test cases that a QA
lead would sign off on. A single "generate test cases from this requirement" LLM call
produces shallow, redundant output and offers no traceability for *why* a case exists.

We want the system to reason like a senior QA engineer — understanding intent, deriving
business rules, weighing risk, checking existing coverage, and critiquing its own draft
before presenting it.

## Decision

Implement an **Agent Orchestrator** that runs a deliberate multi-step pipeline, where each
step's output feeds the next:

```
analyze → extract business rules → risk analysis → retrieve (RAG) →
detect coverage gaps → generate → self-review
```

The orchestrator coordinates specialized tools — a **requirement analyzer**, a **RAG
tool** ([ADR-0003](./0003-rag-with-chromadb.md)), and a **coverage tool** — and calls the
configured LLM provider ([ADR-0002](./0002-pluggable-llm-provider.md)). Output is
structured (Pydantic v2) and every generated case is traceable to a rule, risk, or gap.
The **self-review** step is first-class, not optional.

## Consequences

**Positive**
- Higher-signal output; the self-review step actively prunes redundancy and untestable cases.
- Traceability (case → rule / risk / gap) makes output reviewable and defensible.
- RAG grounding keeps generation consistent with the team's existing tests.
- Modular steps can be evaluated, tuned, or toggled independently.

**Negative / trade-offs**
- **Latency & cost** — multiple LLM calls per requirement vs. one. Mitigations: cache the
  analysis step, allow step toggles, stream partial results (future).
- More moving parts to build, test, and observe than a single call.
- Step-to-step error propagation needs handling so one weak step doesn't poison the rest.

## Alternatives considered

- **Single-shot generation** — cheapest/fastest but low signal and no traceability;
  contradicts the core product thesis. Rejected.
- **Fully autonomous open-ended agent loop** — flexible but unpredictable latency/cost and
  harder to evaluate; rejected in favor of a fixed, inspectable pipeline for MVP.
