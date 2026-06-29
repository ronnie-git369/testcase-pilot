"""CoverageReport — the result of comparing a Requirement to existing tests.

This is intentionally NOT a field on Requirement: it's an analysis *about* a
requirement (produced by CoverageAnalyzer, returned by the coverage endpoint),
not part of the requirement's own structure.
"""

from pydantic import BaseModel, Field


class CoverageReport(BaseModel):
    """What existing tests already cover, and what is still missing."""

    covered: list[str] = Field(
        default_factory=list,
        description="Aspects of the requirement already covered by existing tests.",
    )
    gaps: list[str] = Field(
        default_factory=list,
        description="Aspects not yet covered — the testing gaps to fill.",
    )
