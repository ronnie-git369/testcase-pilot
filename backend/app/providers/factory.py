"""Provider factory — selects the configured LLM provider from the environment.

`LLM_PROVIDER` chooses the backend (default 'ollama') so callers depend on the
abstraction, never on a concrete vendor (ADR-0002). Adding Claude/OpenAI later
is one new branch here plus an adapter — no change to the agents.

This function is used as a FastAPI dependency; tests override it with a fake.
"""

from __future__ import annotations

import os

from app.providers.base import LLMProvider
from app.providers.ollama_provider import OllamaProvider


def get_llm_provider() -> LLMProvider:
    """Return the LLM provider named by the LLM_PROVIDER env var."""
    name = os.getenv("LLM_PROVIDER", "ollama").lower()
    if name == "ollama":
        return OllamaProvider()
    raise ValueError(f"Unknown LLM_PROVIDER: {name!r}")
