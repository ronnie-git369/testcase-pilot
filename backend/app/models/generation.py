"""GenerationResult — the full output of the end-to-end pipeline.

Bundles what the system understood (the enriched Requirement), its gap analysis
(CoverageReport), and the final reviewed TestCases. The requirement + coverage
double as the *rationale*: they explain why each generated case exists.
"""

from pydantic import BaseModel, Field

from app.models.coverage import CoverageReport
from app.models.requirement import Requirement
from app.models.test_case import TestCase


class GenerationResult(BaseModel):
    """The end-to-end result of POST /requirements/generate."""

    requirement: Requirement
    coverage: CoverageReport = Field(default_factory=CoverageReport)
    test_cases: list[TestCase] = Field(default_factory=list)
