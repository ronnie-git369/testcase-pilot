"""RequirementParserService — turns a Markdown requirement into a Requirement.

Responsibility (ONLY this): convert raw requirement text into structured data.
It does not analyze, generate, score, call an LLM, or do any I/O. That keeps it
deterministic and makes it a clean tool for a future agent orchestrator to call.

Design: a single pass (`_tokenize`) reads the document once into a feature name
plus a map of {section heading -> content lines}. Small field extractors then
read from that structure. One pass, O(n), one place that understands Markdown.
"""

# Makes all annotations lazy (PEP 563), so modern hints like `str | None`
# work on Python 3.9 (where PEP 604 unions aren't yet runtime-evaluable).
from __future__ import annotations

from app.models import Requirement

# Default used when the document has no usable feature heading. We default
# rather than crash (resilient batch processing) but leave a breadcrumb in
# `notes` so the malformed input is observable, never silent.
DEFAULT_FEATURE = "Untitled"
MISSING_FEATURE_NOTE = "No feature heading found; defaulted to 'Untitled'."

# Section headings we recognize, normalized (lowercased). Adding a new section
# is a one-line change here plus a reader in parse().
_USER_STORY = "user story"
_ACCEPTANCE_CRITERIA = "acceptance criteria"


class RequirementParserService:
    """Parses a Markdown requirement document into a Requirement model."""

    def parse(self, markdown: str) -> Requirement:
        """Convert raw Markdown into a structured Requirement.

        `business_rules` and `risks` are intentionally left empty — extracting
        those is a future (probabilistic) agent's job, not the parser's.
        """
        feature, sections = self._tokenize(markdown)

        notes: list[str] = []
        if feature is None:
            feature = DEFAULT_FEATURE
            notes.append(MISSING_FEATURE_NOTE)

        user_story = " ".join(sections.get(_USER_STORY, []))
        acceptance_criteria = self._extract_bullets(sections.get(_ACCEPTANCE_CRITERIA, []))

        return Requirement(
            feature=feature,
            user_story=user_story,
            acceptance_criteria=acceptance_criteria,
            notes=notes,
        )

    def _tokenize(self, markdown: str) -> tuple[str | None, dict[str, list[str]]]:
        """Read the document once into (feature, {heading: [content lines]}).

        Single pass, O(n). The `current` variable is the state machine: it holds
        which section we're inside. An H1 sets the feature and closes the current
        section; an H2 opens a new section; everything else is content routed to
        the current section (or ignored if we're not inside one).
        """
        feature: str | None = None
        sections: dict[str, list[str]] = {}
        current: str | None = None

        for raw_line in markdown.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("## "):  # H2 -> open a section
                current = line[3:].strip().lower()
                sections.setdefault(current, [])  # remember it even if empty
                continue

            if line.startswith("# "):  # H1 -> feature; closes any section
                name = self._strip_feature_label(line[2:].strip())
                if name and feature is None:  # first non-empty H1 wins
                    feature = name
                current = None
                continue

            if current is not None:  # content under the open section
                sections[current].append(line)

        return feature, sections

    @staticmethod
    def _strip_feature_label(text: str) -> str:
        """Drop an optional, case-insensitive leading `Feature:` label."""
        if text.lower().startswith("feature:"):
            return text[len("feature:"):].strip()
        return text

    @staticmethod
    def _extract_bullets(lines: list[str]) -> list[str]:
        """Turn `-`/`*` bullet lines into a clean list; ignore everything else.

        Non-bullet lines under the section (stray prose) and empty bullets are
        skipped, so only real, non-empty criteria survive.
        """
        bullets: list[str] = []
        for line in lines:
            if line.startswith("- ") or line.startswith("* "):
                text = line[2:].strip()
                if text:
                    bullets.append(text)
        return bullets
