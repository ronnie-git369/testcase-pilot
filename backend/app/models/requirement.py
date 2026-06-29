"""The Requirement domain model.

This is the central contract of TestCasePilot. A `Requirement` is the structured
form of a software requirement after parsing. Today it is produced by
`RequirementParserService`; later, agents (BusinessRuleExtractor, RiskAnalyzer,
CoverageAnalyzer, TestGeneratorAgent) read from and write to this same shape.

It is a pure data structure: no parsing, no I/O, no LLM calls.
"""

from pydantic import BaseModel, Field


class Requirement(BaseModel):
    """A software requirement after it has been parsed into structured data."""

    feature: str = Field(
        ...,
        description="Short name of the feature this requirement belongs to.",
    )
    user_story: str = Field(
        default="",
        description="Narrative intent: as a <role> I want <goal> so that <benefit>.",
    )
    acceptance_criteria: list[str] = Field(
        default_factory=list,
        description="Testable conditions that must hold for the feature to be accepted.",
    )
    business_rules: list[str] = Field(
        default_factory=list,
        description="Domain constraints. Filled later by the BusinessRuleExtractor.",
    )
    risks: list[str] = Field(
        default_factory=list,
        description="Risk areas to prioritize coverage. Filled later by the RiskAnalyzer.",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Free-form notes that do not fit the structured fields.",
    )
