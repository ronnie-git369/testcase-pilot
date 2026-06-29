"""Unit tests for the Requirement domain model.

We are NOT testing Pydantic itself (the library is already tested). We are
testing *our design decisions*:
  - `feature` is required.
  - the list/text fields have sensible, empty defaults.
  - those defaults are independent per instance (the mutable-default trap).
  - a fully-populated requirement preserves every field.
"""

import pytest
from pydantic import ValidationError

from app.models import Requirement


def test_feature_is_required():
    """A Requirement with no `feature` must be rejected.

    Prevents: a malformed requirement (no anchor feature) flowing silently
    downstream to future agents. We chose fail-fast at the boundary.
    """
    with pytest.raises(ValidationError):
        Requirement()  # type: ignore[call-arg]


def test_minimal_requirement_has_empty_defaults():
    """Only `feature` is needed; everything else defaults to empty.

    Prevents: defaults drifting to `None` or unexpected values, which would
    force every downstream consumer to write None-checks before iterating.
    """
    req = Requirement(feature="Login")

    assert req.feature == "Login"
    assert req.user_story == ""
    assert req.acceptance_criteria == []
    assert req.business_rules == []
    assert req.risks == []
    assert req.notes == []


def test_list_defaults_are_independent_per_instance():
    """Each instance gets its OWN list objects, not a shared one.

    Prevents: the classic Python mutable-default bug. If defaults were
    `= []`, mutating one requirement's list could leak into another.
    This is the single highest-value test in this file.
    """
    a = Requirement(feature="A")
    b = Requirement(feature="B")

    a.acceptance_criteria.append("criterion for A")

    assert a.acceptance_criteria == ["criterion for A"]
    assert b.acceptance_criteria == []  # b is untouched


def test_fully_populated_requirement_round_trips():
    """A requirement with every field set serializes back to the same data.

    Prevents: silent contract regressions (a renamed/dropped field) that
    would break every agent reading this model.
    """
    data = {
        "feature": "Checkout",
        "user_story": "As a shopper I want to pay so that I can complete my order",
        "acceptance_criteria": ["card payment succeeds", "invalid card is rejected"],
        "business_rules": ["orders over $10k need manual approval"],
        "risks": ["payment gateway timeout"],
        "notes": ["see PCI compliance doc"],
    }

    req = Requirement(**data)

    assert req.model_dump() == data
