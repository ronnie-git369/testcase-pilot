"""HTTP route for Playwright spec generation (POST /tests/playwright).

Additive endpoint: turns already-generated TestCases into a runnable Playwright
spec skeleton. Deterministic (no LLM, no I/O) — the extension sends the cases it
already has and the codegen runs server-side, keeping the client thin.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.models import TestCase
from app.services.playwright_generator import render_playwright_spec, spec_filename

router = APIRouter(prefix="/tests", tags=["tests"])


class PlaywrightRequest(BaseModel):
    """Request body for POST /tests/playwright."""

    feature: str = Field(default="Feature", description="Feature name for describe()/filename.")
    test_cases: list[TestCase] = Field(default_factory=list)


class PlaywrightSpec(BaseModel):
    """A generated Playwright spec file: suggested name + TypeScript code."""

    filename: str
    code: str


@router.post("/playwright", response_model=PlaywrightSpec)
def generate_playwright(request: PlaywrightRequest) -> PlaywrightSpec:
    """Render a Playwright spec skeleton from the provided test cases."""
    return PlaywrightSpec(
        filename=spec_filename(request.feature),
        code=render_playwright_spec(request.feature, request.test_cases),
    )
