"""LLM provider abstractions and adapters.

`LLMProvider` is the port; concrete adapters (added incrementally) plug into it.
Keeping providers in their own package means agents depend on the abstraction,
not on any vendor SDK.
"""

from app.providers.base import LLMProvider
from app.providers.factory import get_llm_provider
from app.providers.ollama_provider import OllamaError, OllamaProvider

__all__ = ["LLMProvider", "OllamaProvider", "OllamaError", "get_llm_provider"]
