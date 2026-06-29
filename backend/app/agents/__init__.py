"""LLM-backed agents.

Each agent takes structured input (e.g. a Requirement), prompts an injected
LLMProvider, and returns validated structured output. They depend on the
provider abstraction, never on a concrete vendor.
"""

from app.agents.business_rule_extractor import (
    BusinessRuleExtractionError,
    BusinessRuleExtractor,
)

__all__ = ["BusinessRuleExtractor", "BusinessRuleExtractionError"]
