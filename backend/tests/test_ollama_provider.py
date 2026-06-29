"""Smoke test for the real OllamaProvider.

This needs a running Ollama server with the configured model pulled. It is
SKIPPED automatically when Ollama isn't reachable, so the suite stays green in
CI and on machines without Ollama. Run it locally after `ollama serve`.
"""

import os

import httpx
import pytest

from app.providers.ollama_provider import DEFAULT_HOST, OllamaProvider


def _ollama_running() -> bool:
    host = os.getenv("OLLAMA_HOST", DEFAULT_HOST).rstrip("/")
    try:
        httpx.get(host, timeout=1.0)
        return True
    except httpx.HTTPError:
        return False


@pytest.mark.skipif(not _ollama_running(), reason="Ollama not reachable locally")
def test_ollama_completes_a_prompt():
    """A live model returns a non-empty string for a trivial prompt."""
    out = OllamaProvider().complete("Reply with exactly one word: pong")

    assert isinstance(out, str)
    assert out.strip() != ""
