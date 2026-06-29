"""TestCase / TestSuite — the generated output of TestCasePilot.

A TestCase is enterprise-quality: structured steps + expected result, a type and
priority, and `covers` for traceability (which rule / risk / coverage gap it
addresses). TestSuite is the wrapper the LLM's JSON validates into.
"""

from pydantic import BaseModel, Field


class TestCase(BaseModel):
    """A single review-ready manual test case."""

    title: str
    type: str = Field(description="positive | negative | edge | security | ...")
    priority: str = Field(description="high | medium | low")
    steps: list[str] = Field(default_factory=list)
    expected_result: str = ""
    covers: str = Field(
        default="",
        description="The rule, risk, or coverage gap this case addresses (traceability).",
    )


class TestSuite(BaseModel):
    """A set of generated test cases (the schema the generator validates into)."""

    cases: list[TestCase] = Field(default_factory=list)
