"""GenerationOrchestrator — runs the full requirement -> tests pipeline.

Chains the deterministic parser with the LLM agents and the retriever:
parse -> business rules -> risks -> coverage -> generate -> self-review.

Each LLM stage degrades gracefully: if a stage raises its domain error (e.g.
unparseable output after retries), the pipeline records a note on the requirement
and continues with a sensible default — so a single flaky stage never sinks the
whole request. This mirrors the parser's "permissive but observable" principle.
(Provider/connectivity errors are NOT swallowed; they surface honestly.)
"""

from __future__ import annotations

from typing import Callable, TypeVar

from app.agents import (
    BusinessRuleExtractionError,
    BusinessRuleExtractor,
    CoverageAnalysisError,
    CoverageAnalyzer,
    RiskAnalysisError,
    RiskAnalyzer,
    SelfReviewer,
    SelfReviewError,
    TestGenerationError,
    TestGeneratorAgent,
)
from app.models import CoverageReport, GenerationResult, Requirement
from app.services.requirement_parser import RequirementParserService

T = TypeVar("T")


class GenerationOrchestrator:
    """Composes the parser + agents into one parse-to-test-cases pipeline."""

    def __init__(
        self,
        parser: RequirementParserService,
        rule_extractor: BusinessRuleExtractor,
        risk_analyzer: RiskAnalyzer,
        coverage_analyzer: CoverageAnalyzer,
        generator: TestGeneratorAgent,
        reviewer: SelfReviewer,
    ) -> None:
        self._parser = parser
        self._rule_extractor = rule_extractor
        self._risk_analyzer = risk_analyzer
        self._coverage_analyzer = coverage_analyzer
        self._generator = generator
        self._reviewer = reviewer

    def run(self, markdown: str) -> GenerationResult:
        """Run the full pipeline and return the assembled result."""
        requirement = self._parser.parse(markdown)

        requirement.business_rules = self._safe(
            lambda: self._rule_extractor.extract(requirement),
            default=[],
            requirement=requirement,
            error=BusinessRuleExtractionError,
            note="Business-rule extraction failed; continuing without rules.",
        )
        requirement.risks = self._safe(
            lambda: self._risk_analyzer.analyze(requirement),
            default=[],
            requirement=requirement,
            error=RiskAnalysisError,
            note="Risk analysis failed; continuing without risks.",
        )
        coverage = self._safe(
            lambda: self._coverage_analyzer.analyze(requirement),
            default=CoverageReport(),
            requirement=requirement,
            error=CoverageAnalysisError,
            note="Coverage analysis failed; continuing without coverage.",
        )
        draft = self._safe(
            lambda: self._generator.generate(requirement, gaps=coverage.gaps),
            default=[],
            requirement=requirement,
            error=TestGenerationError,
            note="Test generation failed; no cases produced.",
        )
        final = self._safe(
            lambda: self._reviewer.review(requirement, draft),
            default=draft,
            requirement=requirement,
            error=SelfReviewError,
            note="Self-review failed; returning unreviewed draft cases.",
        )

        return GenerationResult(
            requirement=requirement, coverage=coverage, test_cases=final
        )

    @staticmethod
    def _safe(
        call: Callable[[], T],
        *,
        default: T,
        requirement: Requirement,
        error: type[Exception],
        note: str,
    ) -> T:
        """Run `call`; on its domain `error`, record `note` and return `default`."""
        try:
            return call()
        except error:
            requirement.notes.append(note)
            return default
