# ADR-0002: Pluggable LLM provider abstraction

- **Status:** Accepted
- **Date:** 2026-06-29
- **Deciders:** Engineering

## Context

Test-case generation depends on an LLM, but teams differ on the right one. Drivers:

- **Cost** — cloud frontier models vs. cheaper or local options.
- **Latency** — local models can be faster for some workloads, slower for others.
- **Data residency / privacy** — some teams cannot send requirements to a third-party
  API and need an on-prem/local model.
- **Quality** — different providers/models perform differently on QA reasoning.

Hard-coding a single provider would force one set of trade-offs on every user and make
evaluation across providers painful.

## Decision

Treat the LLM provider as a **pluggable, configuration-driven dependency**. Backend code
must not hard-code a single provider; it depends on a provider interface and selects the
concrete implementation at runtime from environment variables:

- `OPENAI_API_KEY` → OpenAI
- `ANTHROPIC_API_KEY` → Anthropic Claude
- `OLLAMA_HOST` → local Ollama

Credentials live only in a git-ignored `backend/.env`. When building the Claude/Anthropic
integration, consult the `claude-api` skill for current model IDs and patterns.

## Consequences

**Positive**
- Teams choose their cost/latency/privacy trade-off with no code change.
- Local Ollama path enables fully on-prem operation.
- A clean interface makes provider A/B evaluation straightforward.

**Negative / trade-offs**
- Lowest-common-denominator risk — provider-specific features (e.g. native tool use,
  prompt caching) need careful abstraction or capability flags.
- More surface to test: each provider path needs its own integration coverage.
- Output quality varies by provider; the self-review pipeline step
  ([ADR-0004](./0004-agent-orchestration-pipeline.md)) helps normalize quality.

## Alternatives considered

- **Single provider (e.g. OpenAI only)** — simplest, but rejected: blocks privacy-sensitive
  and cost-sensitive users.
- **Third-party gateway/proxy (LiteLLM-style)** — viable later; for MVP a thin in-house
  interface keeps dependencies minimal and pinned.
