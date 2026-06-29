"""HTTP routes for TestCasePilot (the interface-adapter layer).

Routes are deliberately THIN: they translate HTTP <-> domain and delegate all
logic to application services. No business logic lives here. The dependency
arrow points inward — routes depend on services, never the reverse.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agents import BusinessRuleExtractor, CoverageAnalyzer, RiskAnalyzer
from app.models import CoverageReport, Requirement
from app.providers import LLMProvider, get_llm_provider
from app.retrieval import TestCaseRetriever, get_retriever
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


def get_business_rule_extractor(
    provider: LLMProvider = Depends(get_llm_provider),
) -> BusinessRuleExtractor:
    """Provide the extractor with an injected (env-configured) LLM provider.

    Tests override `get_llm_provider` to swap in a fake — so this endpoint is
    exercisable without a running model.
    """
    return BusinessRuleExtractor(provider)


@router.post("/business-rules", response_model=Requirement)
def extract_business_rules(
    request: ParseRequirementRequest,
    parser: RequirementParserService = Depends(get_parser),
    extractor: BusinessRuleExtractor = Depends(get_business_rule_extractor),
) -> Requirement:
    """Parse Markdown, then fill in business rules via the LLM agent.

    This is the first composed pipeline step: deterministic parse -> probabilistic
    extraction. The route stays the orchestrator; each piece keeps its own job.
    """
    requirement = parser.parse(request.markdown)
    requirement.business_rules = extractor.extract(requirement)
    return requirement


def get_risk_analyzer(
    provider: LLMProvider = Depends(get_llm_provider),
) -> RiskAnalyzer:
    """Provide the risk analyzer with an injected (env-configured) LLM provider."""
    return RiskAnalyzer(provider)


@router.post("/risks", response_model=Requirement)
def analyze_risks(
    request: ParseRequirementRequest,
    parser: RequirementParserService = Depends(get_parser),
    analyzer: RiskAnalyzer = Depends(get_risk_analyzer),
) -> Requirement:
    """Parse Markdown, then fill in testing risks via the LLM agent."""
    requirement = parser.parse(request.markdown)
    requirement.risks = analyzer.analyze(requirement)
    return requirement


def get_coverage_analyzer(
    provider: LLMProvider = Depends(get_llm_provider),
    retriever: TestCaseRetriever = Depends(get_retriever),
) -> CoverageAnalyzer:
    """Provide the coverage analyzer with an injected provider + retriever."""
    return CoverageAnalyzer(provider, retriever)


@router.post("/coverage", response_model=CoverageReport)
def analyze_coverage(
    request: ParseRequirementRequest,
    parser: RequirementParserService = Depends(get_parser),
    extractor: BusinessRuleExtractor = Depends(get_business_rule_extractor),
    analyzer: CoverageAnalyzer = Depends(get_coverage_analyzer),
) -> CoverageReport:
    """Parse Markdown, extract business rules, then report coverage gaps.

    A three-stage pipeline: deterministic parse -> probabilistic rule extraction
    -> retrieval-grounded coverage analysis. The closest thing yet to the full
    orchestrator. (FastAPI caches get_llm_provider within the request, so the
    extractor and analyzer share one provider instance.)
    """
    requirement = parser.parse(request.markdown)
    requirement.business_rules = extractor.extract(requirement)
    return analyzer.analyze(requirement)
