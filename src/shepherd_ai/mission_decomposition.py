"""Bounded decomposition of explicit multi-clause mission commands."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from shepherd_ai.intent import MissionIntent, parse_intent


DECOMPOSER_NAME = "bounded_explicit_drone_clause_decomposer_v1"

_COUNT_TOKEN = r"(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)"
_BOUNDARY = re.compile(
    rf"\s+(?:and|then)\s+(?=(?:(?:send|dispatch|deploy|use)\s+)?{_COUNT_TOKEN}\s+(?:more\s+)?drones?\b)",
    flags=re.IGNORECASE,
)
_EXPLICIT_DRONE_GROUP = re.compile(
    rf"\b{_COUNT_TOKEN}\s+(?:more\s+)?drones?\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class MissionClause:
    """One explicitly bounded mission clause and its parsed intent."""

    clause_id: str
    text: str
    intent: MissionIntent

    def to_dict(self) -> dict[str, Any]:
        return {
            "clause_id": self.clause_id,
            "text": self.text,
            "intent": self.intent.to_dict(),
        }


@dataclass(frozen=True)
class MissionDecomposition:
    """Inspectable result that never guesses an unsupported clause boundary."""

    status: str
    decomposer: str
    source_text: str
    clauses: tuple[MissionClause, ...]
    total_requested_drones: int | None
    issues: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "decomposer": self.decomposer,
            "source_text": self.source_text,
            "clauses": [clause.to_dict() for clause in self.clauses],
            "total_requested_drones": self.total_requested_drones,
            "issues": list(self.issues),
        }


def decompose_mission_command(command: str) -> MissionDecomposition:
    """Split only at conjunctions followed by an explicit drone group.

    This rule covers the roadmap scenario while avoiding semantic guessing for
    conjunctions such as ``inspect crops and irrigation``. Commands containing
    multiple explicit groups but no supported boundary request clarification.
    """

    source_text = command.strip()
    if not source_text:
        raise ValueError("command must not be empty")

    group_count = len(_EXPLICIT_DRONE_GROUP.findall(source_text))
    raw_clauses = [_strip_terminal_punctuation(value) for value in _BOUNDARY.split(source_text)]
    if group_count > 1 and len(raw_clauses) == 1:
        return MissionDecomposition(
            status="clarification_required",
            decomposer=DECOMPOSER_NAME,
            source_text=source_text,
            clauses=(),
            total_requested_drones=None,
            issues=("multiple_drone_groups_without_supported_boundary",),
        )

    clauses = tuple(
        MissionClause(
            clause_id=f"clause_{index:03d}",
            text=text,
            intent=parse_intent(text),
        )
        for index, text in enumerate(raw_clauses, start=1)
    )
    counts = [clause.intent.count for clause in clauses]
    total = sum(count for count in counts if isinstance(count, int))
    issues = tuple(
        f"{clause.clause_id}_count_not_resolved"
        for clause in clauses
        if not isinstance(clause.intent.count, int)
    )
    return MissionDecomposition(
        status="decomposed" if len(clauses) > 1 else "single_clause",
        decomposer=DECOMPOSER_NAME,
        source_text=source_text,
        clauses=clauses,
        total_requested_drones=total if not issues else None,
        issues=issues,
    )


def _strip_terminal_punctuation(text: str) -> str:
    return text.strip().rstrip(".?!").strip()
