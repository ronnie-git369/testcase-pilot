# TestCasePilot

> An Agentic AI QA assistant that generates enterprise-quality test cases from software requirements.

TestCasePilot helps QA engineers turn raw requirements into comprehensive, review-ready
test cases. Instead of producing a flat list of generated tests, it works like a senior
QA engineer — reasoning about the requirement, mining existing coverage, and critiquing
its own output before presenting results.

## Vision

Given a software requirement, TestCasePilot:

1. **Analyzes** the requirement to understand intent and scope
2. **Extracts business rules** that the system must enforce
3. **Performs risk analysis** to prioritize what matters most
4. **Finds existing test cases** using retrieval-augmented generation (RAG)
5. **Detects missing coverage** by comparing intent against what already exists
6. **Generates** enterprise-quality test cases
7. **Reviews its own output** before presenting the final result

The goal is depth over volume: fewer, higher-signal test cases that a QA lead would
actually sign off on.

## Tech Stack

| Layer        | Technology                          |
| ------------ | ----------------------------------- |
| Backend API  | FastAPI · Python · Uvicorn          |
| Data models  | Pydantic v2                         |
| Retrieval    | RAG · ChromaDB                      |
| Agent / LLM  | OpenAI · Claude · Ollama            |
| Client       | VS Code Extension · TypeScript      |

## Architecture

```
                 User
                  │
                  ▼
         VS Code Extension
                  │
                  ▼
          FastAPI Backend
                  │
          Agent Orchestrator
                  │
      ┌───────────┼───────────┐
      ▼           ▼           ▼
 Requirement   RAG Tool   Coverage Tool
      │           │           │
      └───────────┼───────────┘
                  ▼
            AI Provider
      (OpenAI / Claude / Ollama)
                  │
                  ▼
      Enterprise Test Cases
```

The **VS Code extension** sends a requirement to the **FastAPI backend**, which hands it
to the **Agent Orchestrator**. The orchestrator coordinates specialized tools — a
**Requirement** analyzer, a **RAG tool** for finding existing test cases, and a
**Coverage tool** for detecting gaps — and calls a configurable **AI provider** to
produce the final **enterprise test cases**.

## Project Structure

```
testcase-pilot/
├── backend/            # FastAPI service (agent orchestration + RAG API)
│   ├── app/            # Application package (imported as app.main:app)
│   │   ├── main.py     # FastAPI entrypoint — root banner + /health
│   │   ├── api/        # API routes (routes.py — placeholder)
│   │   ├── agents/     # Agent orchestration (requirement_agent.py — placeholder)
│   │   ├── models/     # Pydantic models (requirement.py — placeholder)
│   │   └── services/   # Services, e.g. requirement parsing (placeholder)
│   └── requirements.txt
├── extension/          # VS Code extension (TypeScript client)
├── prompts/            # Agent prompt templates
├── examples/           # Sample requirements and generated test cases
├── docs/               # Design notes and documentation (e.g. git-commit-guide.md)
├── tests/              # Test suite
├── LICENSE
└── README.md
```

> **Status:** Early scaffold. The backend dependencies and project layout are in place
> and the FastAPI entrypoint (`app/main.py`) serves a root banner and `/health` check.
> The `api/`, `agents/`, `models/`, and `services/` packages are empty placeholders, and
> the agent, RAG, and extension implementations are still to come. Directories not yet
> listed above (`extension/`, `prompts/`, `examples/`, `tests/`) are intended structure
> and may currently be empty.

## Getting Started

### Prerequisites

- Python 3.9+
- (Optional) An LLM provider: an OpenAI or Anthropic API key, or a local [Ollama](https://ollama.com) install

### Backend setup

```bash
cd backend

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the API

The application entrypoint lives at `app/main.py` (exposing a FastAPI `app`). From
inside `backend/`:

```bash
uvicorn app.main:app --reload
```

The service will be available at http://127.0.0.1:8000, with interactive docs at
http://127.0.0.1:8000/docs. A `GET /` returns a service banner and `GET /health`
returns a health check.

### Configuration

LLM provider credentials are read from environment variables (kept out of version
control via `.gitignore`). Create a `.env` file in `backend/`:

```bash
# Choose a provider
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
# or point at a local Ollama instance
OLLAMA_HOST=http://localhost:11434
```

### VS Code extension

The extension is a thin TypeScript client over the backend. With the API running,
build it and launch it in an Extension Development Host:

```bash
cd extension
npm install        # first time only
npm run compile    # or `npm run watch` to rebuild on change
```

Open the `extension/` folder in VS Code and press **F5** to launch the dev host.
Inside that window there are two ways to generate test cases:

- **Form UI** — run **TestCasePilot: New Requirement (Form)** from the Command
  Palette, or click the 🧪 button in the editor toolbar (shown on Markdown files).
  Fill in the feature, user story, and acceptance criteria, then **Generate test
  cases**. The full report opens beside the form.
- **From a file** — open a Markdown requirement and run **TestCasePilot: Generate
  Test Cases** to send the whole document (or the current selection).

The backend URL defaults to `http://127.0.0.1:8000`; override it with the
`testcasePilot.apiUrl` setting.

## Backend Dependencies

Pinned in [`backend/requirements.txt`](backend/requirements.txt):

- **fastapi** — web framework for the API
- **uvicorn** — ASGI server
- **pydantic** / **pydantic-core** — request/response models and validation
- **starlette**, **anyio**, **h11** — ASGI/async plumbing (FastAPI dependencies)

## Documentation

- [**Milestone Walkthrough**](docs/milestones.md) — how the project was built so far and
  *why*, with a progress tracker (currently ~98%)
- [**API Reference & Guide**](docs/api.md) — endpoints, how a request flows, and how to run the API
- [System Architecture](docs/architecture.md) · [Architecture Decision Records](docs/adr/README.md) · [Diagrams](docs/diagrams/README.md)

## Roadmap

- [x] Backend application entrypoint (`app/main.py` with root banner + `/health`)
- [x] API routes (`app/api/routes.py`) — parse, business-rules, risks, coverage, generate, retrieval
- [x] Agent orchestration pipeline (analyze → extract → risk → retrieve → gap → generate → review)
- [x] ChromaDB-backed RAG over existing test cases
- [x] Pluggable LLM providers — `LLMProvider` port + Ollama adapter (Claude/OpenAI adapters TBD)
- [x] VS Code extension client (thin TypeScript client in `extension/`)
- [x] Example requirements and golden test cases (`examples/`; more TBD)
- [x] Test suite (77 backend tests + extension renderer tests)

## License

See [LICENSE](LICENSE).
