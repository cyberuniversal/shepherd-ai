"""Normalize raw intent constraint strings into bounded structured records.

This is a Week 2 helper for intent extraction output. It does not validate
mission safety or enforce flight rules; it only canonicalizes simple constraint
phrases so later modules can consume less brittle records.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any


CONSTRAINT_NORMALIZER_NAME = "constraint_normalizer_v1"

NUMBER_WORDS_EXTENDED: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
}


@dataclass(frozen=True)
class CanonicalConstraint:
    kind: str
    source_text: str
    parser: str = CONSTRAINT_NORMALIZER_NAME
    relation: str | None = None
    value: int | float | str | None = None
    unit: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def semantic_signature(self) -> tuple[str, str | None, int | float | str | None, str | None]:
        if self.kind == "unparsed_constraint":
            return self.kind, self.relation, _source_signature(self.source_text), self.unit
        return self.kind, self.relation, self.value, self.unit


def normalize_constraints(constraints: list[str]) -> list[CanonicalConstraint]:
    """Normalize raw constraint strings while preserving unparsed constraints."""

    return [normalize_constraint(constraint) for constraint in constraints]


def normalize_constraint(constraint: str) -> CanonicalConstraint:
    """Normalize one raw constraint string.

    Currently supported:

    - altitude ceiling phrases such as ``below fifty meters``
    - ``keep them below 50 metres``

    Unknown constraints are preserved as ``unparsed_constraint`` records.
    """

    source_text = constraint.strip()
    if not source_text:
        raise ValueError("constraint must not be empty")

    normalized = _normalize_text(source_text)
    altitude_value = _extract_altitude_ceiling_meters(normalized)
    if altitude_value is not None:
        return CanonicalConstraint(
            kind="altitude_limit",
            source_text=source_text,
            relation="below",
            value=altitude_value,
            unit="meters",
        )

    return CanonicalConstraint(
        kind="unparsed_constraint",
        source_text=source_text,
        notes=["no_supported_canonical_form"],
    )


def constraint_semantic_signatures(constraints: list[str]) -> set[tuple[str, str | None, int | float | str | None, str | None]]:
    """Return comparable signatures for raw constraints."""

    return {constraint.semantic_signature() for constraint in normalize_constraints(constraints)}


def _extract_altitude_ceiling_meters(text: str) -> int | None:
    patterns = (
        r"\bkeep\s+(?:them|the\s+drones|drones)\s+below\s+(?P<number>[a-z0-9-]+)\s+meters\b",
        r"\b(?:below|under)\s+(?P<number>[a-z0-9-]+)\s+meters\b",
        r"\b(?:no\s+higher\s+than|less\s+than)\s+(?P<number>[a-z0-9-]+)\s+meters\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        return _parse_number(match.group("number"))
    return None


def _parse_number(token: str) -> int | None:
    normalized = token.strip().lower().replace("-", " ")
    if normalized.isdigit():
        return int(normalized)
    if normalized in NUMBER_WORDS_EXTENDED:
        return NUMBER_WORDS_EXTENDED[normalized]
    parts = normalized.split()
    if len(parts) == 2 and parts[0] in NUMBER_WORDS_EXTENDED and parts[1] in NUMBER_WORDS_EXTENDED:
        first = NUMBER_WORDS_EXTENDED[parts[0]]
        second = NUMBER_WORDS_EXTENDED[parts[1]]
        if first >= 20 and second < 10:
            return first + second
    return None


def _normalize_text(text: str) -> str:
    text = text.lower().replace("metres", "meters")
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _source_signature(text: str) -> str:
    return _normalize_text(text).replace("-", " ")
