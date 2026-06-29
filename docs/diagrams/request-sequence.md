# Request Sequence Diagram

End-to-end sequence for a single test-case generation request, from the engineer's action
in VS Code through the backend pipeline and back.

```mermaid
sequenceDiagram
    actor User as QA Engineer
    participant Ext as VS Code Extension
    participant API as FastAPI Backend
    participant Orch as Agent Orchestrator
    participant RAG as RAG Tool
    participant DB as ChromaDB
    participant LLM as LLM Provider

    User->>Ext: Select requirement, trigger generate
    Ext->>API: POST /generate { requirement }
    API->>Orch: run pipeline(requirement)

    Orch->>LLM: Analyze intent + extract rules + risk
    LLM-->>Orch: analysis, rules, risks

    Orch->>RAG: retrieve similar cases
    RAG->>DB: vector query
    DB-->>RAG: nearest existing cases
    RAG-->>Orch: retrieved cases

    Orch->>Orch: detect coverage gaps
    Orch->>LLM: generate cases (rules + risks + gaps)
    LLM-->>Orch: draft cases
    Orch->>LLM: self-review / revise
    LLM-->>Orch: final cases

    Orch-->>API: structured test cases (+ rationale)
    API-->>Ext: 200 OK { cases }
    Ext-->>User: Render review-ready cases
```

> The number of LLM calls per request is intentional (see
> [ADR-0004](../adr/0004-agent-orchestration-pipeline.md)); analysis is cacheable and steps
> may be toggled to manage latency and cost.
