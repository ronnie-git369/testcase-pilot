"""HTTP routes for TestCasePilot (the interface-adapter layer).

Routes are deliberately THIN: they translate HTTP <-> domain and delegate all
logic to application services. No business logic lives here. The dependency
arrow points inward — routes depend on services, never the reverse.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.models import Requirement
from app.services import RequirementParserService

# Grouped under /requirements; `tags` controls the section name in /docs.
router = APIRouter(prefix="/requirements", tags=["requirements"])


class ParseRequirementRequest(BaseModel):
    """Request body (a DTO, not a domain entity) for POST /requirements/parse."""

    markdown: str = Field(
        ...,
        description="Raw Markdown requirement text to parse into a Requirement.",
    )


def get_parser() -> RequirementParserService:
    """Provide the parser service.

    A dependency provider so the route receives the service instead of
    constructing it. Tests can override it via `app.dependency_overrides`, and
    later this is where a configured (e.g. provider-aware) instance is wired in.
    """
    return RequirementParserService()


@router.post("/parse", response_model=Requirement)
def parse_requirement(
    request: ParseRequirementRequest,
    parser: RequirementParserService = Depends(get_parser),
) -> Requirement:
    """Parse raw Markdown into a structured Requirement.

    Deterministic and LLM-free. Malformed input is handled permissively by the
    parser (e.g. a missing feature defaults to 'Untitled' with a note), so this
    returns 200 with a best-effort Requirement rather than rejecting the input.
    """
    return parser.parse(request.markdown)
