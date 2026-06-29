"""Domain models for TestCasePilot.

These are pure data structures (Pydantic models). They hold no business logic,
no I/O, and no LLM calls — they only define the *shape* of data that flows
through the system.
"""

from app.models.requirement import Requirement

__all__ = ["Requirement"]
