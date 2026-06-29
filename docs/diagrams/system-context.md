# System Context Diagram

High-level view of TestCasePilot: how a request flows from the user through the editor
extension into the backend, across the orchestrated tools, to the LLM provider, and back
as review-ready test cases.

```mermaid
flowchart TD
    user([QA Engineer])
    ext[VS Code Extension<br/>thin TypeScript client]
    api[FastAPI Backend<br/>api · models · agents · services]
    orch{{Agent Orchestrator<br/>analyze → … → self-review}}

    subgraph tools [Specialized Tools]
        analyzer[Requirement Analyzer]
        rag[RAG Tool]
        coverage[Coverage Tool]
    end

    chroma[(ChromaDB<br/>existing test-case vectors)]
    llm[/LLM Provider<br/>OpenAI · Claude · Ollama/]
    out([Review-ready Test Cases])

    user -->|requirement| ext
    ext -->|HTTP JSON| api
    api --> orch
    orch --> analyzer
    orch --> rag
    orch --> coverage
    rag <--> chroma
    orch -->|prompts| llm
    llm -->|completions| orch
    orch --> out
    out --> ext
    ext --> user
```

> Pluggable provider selection is driven by environment variables — see
> [ADR-0002](../adr/0002-pluggable-llm-provider.md). RAG store rationale in
> [ADR-0003](../adr/0003-rag-with-chromadb.md).
