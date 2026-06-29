"""Shared machinery for JSON-emitting LLM agents.

Extracted once a *third* agent (CoverageAnalyzer) needed the same
prompt -> extract-JSON -> validate -> retry loop — the Rule of Three. Each agent
supplies what *varies* (its prompt, its Pydantic schema, and the domain error to
raise on failure); everything constant lives here.
"""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.providers import LLMProvider

DEFAULT_MAX_ATTEMPTS = 2

T = TypeVar("T", bound=BaseModel)


def extract_json_object(raw: str) -> str:
    """Slice out the JSON object from any prose/markdown the model wraps it in.

    Taking the span from the first '{' to the last '}' tolerates 'Sure! ...'
    chatter and ```json fences without special-casing them.
    """
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in the LLM output.")
    return raw[start : end + 1]


def complete_json(
    provider: LLMProvider,
    prompt: str,
    schema: type[T],
    *,
    error_type: type[Exception],
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> T:
    """Prompt the provider for JSON and validate it into `schema`.

    Retries up to `max_attempts` times (one bad generation shouldn't fail the
    request); raises `error_type` if none parse. `json.JSONDecodeError` is a
    subclass of `ValueError`, so it's covered by the except clause.
    """
    last_error: Exception | None = None
    for _ in range(max_attempts):
        raw = provider.complete(prompt)
        try:
            data = json.loads(extract_json_object(raw))
            return schema.model_validate(data)
        except (ValueError, ValidationError) as exc:
            last_error = exc

    raise error_type(
        "Could not parse a valid JSON response from the LLM output."
    ) from last_error
