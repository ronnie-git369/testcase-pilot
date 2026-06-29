"""Domain models for TestCasePilot.

These are pure data structures (Pydantic models). They hold no business logic,
no I/O, and no LLM calls — they only define the *shape* of data that flows
through the system.
"""

from app.models.coverage import CoverageReport
from app.models.requirement import Requirement
from app.models.test_case import TestCase, TestSuite

__all__ = ["Requirement", "CoverageReport", "TestCase", "TestSuite"]
