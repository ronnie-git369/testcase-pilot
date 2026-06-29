"""OllamaProvider — an LLMProvider adapter for a local Ollama server.

Implements `complete` by calling Ollama's REST API. No API key is needed; the
model runs locally. Configured by environment variables so no caller hard-codes
a host or model (ADR-0002):

  OLLAMA_HOST   default http://localhost:11434
  OLLAMA_MODEL  default llama3.1

Run a model locally first, e.g.:  `ollama pull llama3.1 && ollama serve`
"""

from __future__ import annotations

import os

import httpx

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1"
DEFAULT_TIMEOUT = 120.0  # local models can be slow to generate


class OllamaError(RuntimeError):
    """Raised when the Ollama request fails or returns an unexpected payload."""


class OllamaProvider:
    """Calls a local Ollama server's /api/generate endpoint."""

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        # Explicit arg wins over env var, which wins over the default.
        self._host = (host or os.getenv("OLLAMA_HOST", DEFAULT_HOST)).rstrip("/")
        self._model = model or os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
        self._timeout = timeout

    def complete(self, prompt: str) -> str:
        """Send `prompt` to Ollama and return the model's raw text response."""
        url = f"{self._host}/api/generate"
        # stream=False -> one JSON object back instead of a token stream.
        payload = {"model": self._model, "prompt": prompt, "stream": False}

        try:
            response = httpx.post(url, json=payload, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc

        try:
            return response.json()["response"]
        except (ValueError, KeyError) as exc:
            raise OllamaError(f"Unexpected Ollama response payload: {exc}") from exc
