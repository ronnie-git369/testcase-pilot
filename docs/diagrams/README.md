# Architecture Diagrams

Rendered diagrams for TestCasePilot. We use [Mermaid](https://mermaid.js.org/) so diagrams
live as text in version control and render natively on GitHub.

## Contents

| Diagram | Description |
| --- | --- |
| [system-context.md](./system-context.md) | High-level system context — user, extension, backend, tools, provider |
| [agent-pipeline.md](./agent-pipeline.md) | The multi-step agent reasoning pipeline |
| [request-sequence.md](./request-sequence.md) | End-to-end sequence of a single generation request |

## Conventions

- Prefer Mermaid (`graph`, `flowchart`, `sequenceDiagram`) over binary image files.
- If a binary export (PNG/SVG) is needed for slides, keep the Mermaid source here as the
  source of truth and store exports alongside it.
- Keep diagrams consistent with [`../architecture.md`](../architecture.md); update both
  together.
