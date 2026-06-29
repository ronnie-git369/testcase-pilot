"""Unit tests for GenerationOrchestrator.

Uses the real (deterministic) parser plus stub agents, so we test the *chaining*
and the graceful-degradation behavior without any LLM.
"""

from app.agents import RiskAnalysisError
from app.models import CoverageReport, GenerationResult, TestCase
from app.services import RequirementParserService
from app.services.orchestrator import GenerationOrchestrator


class StubExtractor:
    def extract(self, requirement):
        return ["rule-1"]


class StubRisk:
    def analyze(self, requirement):
        return ["risk-1"]


class FailingRisk:
    def analyze(self, requirement):
        raise RiskAnalysisError("boom")


class StubCoverage:
    def analyze(self, requirement):
        return CoverageReport(covered=["valid login"], gaps=["lockout gap"])


class StubGenerator:
    def __init__(self):
        self.last_gaps = None

    def generate(self, requirement, gaps=None):
        self.last_gaps = gaps
        return [_case("draft")]


class StubReviewer:
    def review(self, requirement, cases):
        return [_case("reviewed")]


def _case(title: str) -> TestCase:
    return TestCase(
        title=title,
        type="security",
        priority="high",
        steps=["do x"],
        expected_result="ok",
        covers="lockout gap",
    )


def build(*, risk=None, generator=None):
    return GenerationOrchestrator(
        RequirementParserService(),
        StubExtractor(),
        risk or StubRisk(),
        StubCoverage(),
        generator or StubGenerator(),
        StubReviewer(),
    )


def test_run_chains_every_stage_in_order():
    generator = StubGenerator()
    result = build(generator=generator).run(
        "# Feature: Login\n## Acceptance Criteria\n- valid login"
    )

    assert isinstance(result, GenerationResult)
    assert result.requirement.feature == "Login"
    assert result.requirement.business_rules == ["rule-1"]
    assert result.requirement.risks == ["risk-1"]
    assert result.coverage.gaps == ["lockout gap"]
    assert generator.last_gaps == ["lockout gap"]  # coverage gaps fed to generator
    assert [c.title for c in result.test_cases] == ["reviewed"]  # review ran last


def test_a_failing_stage_degrades_gracefully():
    """A stage error -> empty field + a note, and the pipeline still finishes.

    Prevents: one flaky LLM stage 500-ing the whole request.
    """
    result = build(risk=FailingRisk()).run("# Feature: Login")

    assert result.requirement.risks == []  # degraded to default
    assert any("Risk analysis failed" in n for n in result.requirement.notes)
    assert [c.title for c in result.test_cases] == ["reviewed"]  # pipeline continued
