"""LLMProvider — the port (abstraction) for language-model backends.

Agents depend on THIS Protocol, never on a concrete vendor SDK (ADR-0002).
Concrete adapters (Ollama, Claude, OpenAI) implement `complete`; a FakeProvider
in tests implements it too, so agent logic is testable offline and for free.

Using a `Protocol` (structural typing) means an adapter is compatible simply by
having a matching `complete` method — it doesn't need to import or subclass this.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """The minimal interface every LLM backend must satisfy."""

    def complete(self, prompt: str) -> str:
        """Send a prompt to the model and return its raw text completion."""
        ...
