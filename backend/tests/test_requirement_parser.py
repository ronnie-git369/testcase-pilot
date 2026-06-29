"""Unit tests for RequirementParserService.

Increment 1 scope: feature extraction only. Each test names the behavior it
locks and the bug it would catch.
"""

from app.models import Requirement
from app.services import RequirementParserService
from app.services.requirement_parser import DEFAULT_FEATURE, MISSING_FEATURE_NOTE


def parse(markdown: str) -> Requirement:
    """Small helper so each test reads as one clear line."""
    return RequirementParserService().parse(markdown)


def test_extracts_feature_from_h1_with_label():
    """`# Feature: X` yields feature 'X' with the label stripped.

    Prevents: leaking the literal 'Feature:' label into the feature name.
    """
    req = parse("# Feature: User Login")

    assert req.feature == "User Login"
    assert req.notes == []  # nothing was defaulted, so no breadcrumb


def test_extracts_feature_from_plain_h1():
    """A plain `# X` heading (no label) is taken verbatim as the feature."""
    req = parse("# User Login")

    assert req.feature == "User Login"


def test_feature_label_is_case_insensitive():
    """`# feature:` / `# FEATURE:` are stripped just like `# Feature:`.

    Prevents: brittleness against human-written casing variations.
    """
    assert parse("# feature: Login").feature == "Login"
    assert parse("# FEATURE: Login").feature == "Login"


def test_h2_is_not_mistaken_for_the_feature():
    """A document with only an H2 has no feature -> default + breadcrumb.

    Prevents: the off-by-one heading bug where `## User Story` is parsed as
    the H1 feature.
    """
    req = parse("## User Story\nAs a user I want to log in")

    assert req.feature == DEFAULT_FEATURE
    assert MISSING_FEATURE_NOTE in req.notes


def test_missing_feature_defaults_and_leaves_breadcrumb():
    """No feature heading -> default 'Untitled' AND an observable note.

    Prevents: SILENT data corruption. This is the whole point of the
    'permissive but observable' design.
    """
    req = parse("Some text with no headings at all")

    assert req.feature == DEFAULT_FEATURE
    assert req.notes == [MISSING_FEATURE_NOTE]


def test_empty_input_defaults_feature():
    """Empty input is handled gracefully, not with a crash."""
    req = parse("")

    assert req.feature == DEFAULT_FEATURE
    assert req.notes == [MISSING_FEATURE_NOTE]


def test_empty_feature_heading_is_treated_as_missing():
    """`# Feature:` with no name is not a usable feature -> default.

    Prevents: accepting an empty string as a 'valid' feature.
    """
    req = parse("# Feature:")

    assert req.feature == DEFAULT_FEATURE
    assert MISSING_FEATURE_NOTE in req.notes


def test_first_valid_h1_wins_over_an_empty_one():
    """An empty heading is skipped; the first non-empty H1 is used."""
    req = parse("# Feature:\n# Login")

    assert req.feature == "Login"
    assert req.notes == []


# --- Increment 2: user story extraction -------------------------------------


def test_extracts_user_story():
    """Text under `## User Story` becomes the user_story field."""
    md = "# Feature: Login\n\n## User Story\nAs a user I want to log in"

    req = parse(md)

    assert req.user_story == "As a user I want to log in"


def test_user_story_heading_is_case_insensitive():
    """`## user story` matches just like `## User Story` (our heading rule)."""
    md = "# Feature: Login\n\n## user story\nAs a user I want to log in"

    assert parse(md).user_story == "As a user I want to log in"


def test_multiline_user_story_is_joined_into_one_statement():
    """Wrapped story lines join with single spaces; blank lines are skipped.

    Prevents: stray newlines/indentation leaking into the stored statement.
    """
    md = (
        "# Feature: Login\n"
        "## User Story\n"
        "As a registered user\n"
        "\n"
        "I want to log in so that I can access my account"
    )

    assert parse(md).user_story == (
        "As a registered user I want to log in so that I can access my account"
    )


def test_user_story_stops_at_the_next_section():
    """A following heading ends the user story; later content is excluded.

    Prevents: the bug where acceptance criteria bleed into the user story
    because the state machine never 'closed' the section.
    """
    md = (
        "# Feature: Login\n"
        "## User Story\n"
        "As a user I want to log in\n"
        "## Acceptance Criteria\n"
        "- valid credentials succeed"
    )

    assert parse(md).user_story == "As a user I want to log in"


def test_no_user_story_section_yields_empty_string():
    """Absent section -> empty string (the model default), not an error."""
    assert parse("# Feature: Login").user_story == ""


def test_feature_and_user_story_together():
    """End-to-end: a well-formed doc fills both fields, no breadcrumbs."""
    md = "# Feature: Login\n\n## User Story\nAs a user I want to log in"

    req = parse(md)

    assert req.feature == "Login"
    assert req.user_story == "As a user I want to log in"
    assert req.notes == []


# --- Increment 3: acceptance criteria + full document -----------------------


def test_extracts_acceptance_criteria_bullets():
    """Each bullet under `## Acceptance Criteria` becomes a list item."""
    md = (
        "# Feature: Login\n"
        "## Acceptance Criteria\n"
        "- Valid credentials grant access\n"
        "- Invalid password shows an error"
    )

    assert parse(md).acceptance_criteria == [
        "Valid credentials grant access",
        "Invalid password shows an error",
    ]


def test_mixed_bullet_markers_are_both_accepted():
    """Both `-` and `*` bullet markers count as criteria."""
    md = "# Feature: Login\n## Acceptance Criteria\n- dash item\n* star item"

    assert parse(md).acceptance_criteria == ["dash item", "star item"]


def test_acceptance_heading_is_case_insensitive():
    """`## acceptance criteria` matches like `## Acceptance Criteria`."""
    md = "# Feature: Login\n## acceptance criteria\n- only item"

    assert parse(md).acceptance_criteria == ["only item"]


def test_non_bullet_and_empty_bullets_under_criteria_are_ignored():
    """Stray prose and empty bullets are skipped; only real criteria survive.

    Prevents: junk lines becoming bogus 'criteria' that future test
    generation would turn into meaningless test cases.
    """
    md = (
        "# Feature: Login\n"
        "## Acceptance Criteria\n"
        "this is prose, not a bullet\n"
        "- real criterion\n"
        "- \n"  # empty bullet
    )

    assert parse(md).acceptance_criteria == ["real criterion"]


def test_no_acceptance_section_yields_empty_list():
    """Absent section -> empty list (model default), not an error."""
    assert parse("# Feature: Login").acceptance_criteria == []


def test_repeated_acceptance_sections_are_merged():
    """Two `## Acceptance Criteria` blocks append into one list (forgiving)."""
    md = (
        "# Feature: Login\n"
        "## Acceptance Criteria\n"
        "- first\n"
        "## Acceptance Criteria\n"
        "- second"
    )

    assert parse(md).acceptance_criteria == ["first", "second"]


def test_business_rules_and_risks_are_never_filled_by_the_parser():
    """SRP boundary: even if those sections exist, the parser leaves them empty.

    Prevents: the parser quietly taking over a future agent's responsibility.
    """
    md = (
        "# Feature: Login\n"
        "## Business Rules\n"
        "- accounts lock after 5 attempts\n"
        "## Risks\n"
        "- brute-force attacks"
    )

    req = parse(md)

    assert req.business_rules == []
    assert req.risks == []


def test_parses_a_full_requirement_document():
    """End-to-end: a complete, well-formed document maps to every field."""
    md = (
        "# Feature: User Login\n"
        "\n"
        "## User Story\n"
        "As a registered user, I want to log in with my email and password\n"
        "so that I can access my account.\n"
        "\n"
        "## Acceptance Criteria\n"
        "- Valid credentials grant access to the dashboard\n"
        "- An invalid password shows an error message\n"
        "- The account locks after 5 consecutive failed attempts\n"
    )

    req = parse(md)

    assert req.feature == "User Login"
    assert req.user_story == (
        "As a registered user, I want to log in with my email and password "
        "so that I can access my account."
    )
    assert req.acceptance_criteria == [
        "Valid credentials grant access to the dashboard",
        "An invalid password shows an error message",
        "The account locks after 5 consecutive failed attempts",
    ]
    assert req.business_rules == []
    assert req.risks == []
    assert req.notes == []
