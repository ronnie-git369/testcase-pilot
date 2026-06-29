# Agent Pipeline Diagram

The multi-step reasoning pipeline the orchestrator runs for each requirement. Each step
feeds the next; the self-review step can loop back to revise before output. See
[ADR-0004](../adr/0004-agent-orchestration-pipeline.md).

```mermaid
flowchart TD
    req([Requirement])
    a[1 · Analyze<br/>intent, scope, actors, preconditions]
    b[2 · Extract Business Rules<br/>explicit + implicit rules]
    c[3 · Risk Analysis<br/>prioritize by impact × likelihood]
    d[4 · Retrieve / RAG<br/>similar existing cases from ChromaDB]
    e[5 · Gap Detection<br/>intended coverage vs. existing]
    f[6 · Generate<br/>cases for rules + risks + gaps]
    g[7 · Self-Review<br/>prune redundancy, check testability]
    out([Review-ready Test Cases<br/>+ rationale, coverage notes])

    chroma[(ChromaDB)]

    req --> a --> b --> c --> d --> e --> f --> g
    d <-.-> chroma
    g -->|revise| f
    g --> out
```

### Step responsibilities

| Step | Output | Notes |
| --- | --- | --- |
| Analyze | Intent, scope, actors, preconditions | Cacheable per requirement |
| Extract rules | Business rules to enforce | Explicit + implicit |
| Risk analysis | Prioritized risk areas | Impact × likelihood |
| Retrieve (RAG) | Similar existing cases | Queries ChromaDB |
| Gap detection | Missing-coverage list | Intended vs. existing |
| Generate | Draft test cases | Targets rules / risks / gaps |
| Self-review | Final cases | First-class critique + revise |
