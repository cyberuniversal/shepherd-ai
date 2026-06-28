"""Typed-command intent extraction baseline.

This module implements the first narrow Shepherd-AI milestone: converting
roadmap-style typed commands into bounded JSON-like mission intents. It is a
deterministic baseline, not a trained NLP model and not a speech recognizer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import re
from typing import Any


NUMBER_WORDS: dict[str, int] = {
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
}

ACTION_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("return", ("return", "come back")),
    ("inspect", ("inspect", "check", "survey")),
    ("scan", ("scan",)),
    ("send", ("send", "dispatch")),
)

LOCATION_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("north", ("north", "northern")),
    ("south", ("south", "southern")),
    ("east", ("east", "eastern")),
    ("west", ("west", "western")),
)

TARGET_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("crops", ("crops", "crop")),
    ("greenhouse", ("greenhouse", "green house")),
    ("irrigation canal", ("irrigation canal", "canal", "irrigation")),
    ("field", ("field",)),
    ("drones", ("drones", "drone")),
)


@dataclass(frozen=True)
class MissionIntent:
    """Structured mission intent emitted by the baseline parser."""

    action: str | None
    count: int | str | None
    location: str | None
    target: str | None
    constraints: list[str] = field(default_factory=list)
    text: str = ""
    parser: str = "deterministic_v0"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def parse_intent(command: str) -> MissionIntent:
    """Parse a typed command into a bounded mission-intent record.

    The baseline intentionally supports only the simple command forms present
    in the roadmap examples. Unknown fields are returned as ``None`` with notes
    rather than guessed.
    """

    text = command.strip()
    if not text:
        raise ValueError("command must not be empty")

    normalized = _normalize(text)
    action = _extract_action(normalized)
    count = _extract_count(normalized)
    location = _extract_location(normalized)
    target = _extract_target(normalized, action)
    constraints = _extract_constraints(normalized)
    notes: list[str] = []

    if count is None and action != "return":
        notes.append("count_not_stated")
    if location is None and action not in {"return"}:
        notes.append("location_not_stated")
    if target is None and action not in {"send", "return"}:
        notes.append("target_not_stated")

    return MissionIntent(
        action=action,
        count=count,
        location=location,
        target=target,
        constraints=constraints,
        text=text,
        notes=notes,
    )


def parse_intents(commands: list[str]) -> list[MissionIntent]:
    """Parse multiple typed commands."""

    return [parse_intent(command) for command in commands]


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_action(text: str) -> str | None:
    # If a command asks to send drones and perform an inspection action, the
    # mission action is the inspection/scanning task rather than transport.
    for action, keywords in ACTION_PATTERNS:
        if any(_contains_word_or_phrase(text, keyword) for keyword in keywords):
            return action
    return None


def _extract_count(text: str) -> int | str | None:
    if _contains_word_or_phrase(text, "all drones") or _contains_word_or_phrase(text, "all drone"):
        return "all"

    digit_match = re.search(r"\b(\d+)\s+drones?\b", text)
    if digit_match:
        return int(digit_match.group(1))

    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\s+drones?\b", text):
            return value

    drone_id_match = re.search(r"\bdrone\s+(\d+)\b", text)
    if drone_id_match:
        return 1

    return None


def _extract_location(text: str) -> str | None:
    for canonical, aliases in LOCATION_ALIASES:
        if any(_contains_word_or_phrase(text, alias) for alias in aliases):
            return canonical
    return None


def _extract_target(text: str, action: str | None) -> str | None:
    if action == "return" and (
        _contains_word_or_phrase(text, "all drones")
        or _contains_word_or_phrase(text, "all drone")
        or _contains_word_or_phrase(text, "drone")
    ):
        return "drones"

    if _contains_word_or_phrase(text, "irrigation canal"):
        return "irrigation canal"

    for canonical, aliases in TARGET_ALIASES:
        if canonical == "drones":
            continue
        if any(_contains_word_or_phrase(text, alias) for alias in aliases):
            return canonical
    return None


def _extract_constraints(text: str) -> list[str]:
    constraints: list[str] = []
    for marker in ("while", "before", "after", "without", "avoid"):
        match = re.search(rf"\b{marker}\b\s+(.+)$", text)
        if match:
            constraints.append(f"{marker} {match.group(1).strip()}")
    return constraints


def _contains_word_or_phrase(text: str, phrase: str) -> bool:
    escaped = re.escape(phrase)
    return re.search(rf"\b{escaped}\b", text) is not None
