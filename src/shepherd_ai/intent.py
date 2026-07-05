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


DETERMINISTIC_PARSER_NAME = "deterministic_v1"

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

TARGET_STOP_MARKERS: tuple[str, ...] = (
    "while",
    "before",
    "after",
    "without",
    "avoid",
    "using",
    "then",
    "below",
)

ACTION_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hold", ("hold position", "hold")),
    ("search", ("search",)),
    ("capture", ("capture", "capture images")),
    ("inspect", ("inspect", "check", "survey")),
    ("scan", ("scan",)),
    ("return", ("return", "come back", "back to base", "back to the base")),
    ("send", ("send", "dispatch")),
)

LOCATION_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("open field", ("open field",)),
    ("north", ("north", "northern")),
    ("south", ("south", "southern")),
    ("east", ("east", "eastern")),
    ("west", ("west", "western")),
)

TARGET_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("stadium entrances", ("stadium entrances", "stadium entrance")),
    ("industrial zone", ("industrial zone",)),
    ("irrigation canal", ("irrigation canal", "canal", "irrigation")),
    ("missing vehicle", ("missing vehicle",)),
    ("railway tracks", ("railway tracks", "railway track", "tracks")),
    ("storage area", ("storage area",)),
    ("parking lot", ("parking lot",)),
    ("water tank", ("water tank",)),
    ("crops", ("crops", "crop")),
    ("greenhouse", ("greenhouse", "green house")),
    ("farm", ("farm",)),
    ("area", ("area",)),
    ("car", ("car",)),
    ("everything", ("everything",)),
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
    parser: str = DETERMINISTIC_PARSER_NAME
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
    if (
        _contains_word_or_phrase(text, "all drones")
        or _contains_word_or_phrase(text, "all drone")
        or _contains_word_or_phrase(text, "all the drones")
        or _contains_word_or_phrase(text, "all available drones")
        or _contains_word_or_phrase(text, "all available drone")
        or _contains_word_or_phrase(text, "every drones")
        or _contains_word_or_phrase(text, "every drone")
        or _contains_word_or_phrase(text, "every available drone")
        or _contains_word_or_phrase(text, "every available drones")
    ):
        return "all"

    count_mentions: list[int] = []
    digit_match = re.search(r"\b(\d+)\s+drones?\b", text)
    if digit_match:
        count_mentions.append(int(digit_match.group(1)))

    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\s+drones?\b", text):
            count_mentions.append(value)
        if re.search(rf"\b{word}\s+more\b", text):
            count_mentions.append(value)

    if count_mentions:
        if re.search(r"\banother(?:\s+drone)?\b", text):
            count_mentions.append(1)
        return sum(count_mentions)

    drone_id_match = re.search(r"\bdrone\s+(\d+)\b", text)
    if drone_id_match:
        return 1

    for word in NUMBER_WORDS:
        if re.search(rf"\bdrone\s+{word}\b", text):
            return 1

    if (
        _contains_word_or_phrase(text, "the drone")
        or _contains_word_or_phrase(text, "nearest drone")
        or _contains_word_or_phrase(text, "whichever drone")
    ):
        return 1

    return None


def _extract_location(text: str) -> str | None:
    matched_locations: list[str] = []
    for canonical, aliases in LOCATION_ALIASES:
        if any(_contains_word_or_phrase(text, alias) for alias in aliases):
            matched_locations.append(canonical)
    if len(matched_locations) == 1:
        return matched_locations[0]
    return None


def _extract_target(text: str, action: str | None) -> str | None:
    if action == "return" and (
        _contains_word_or_phrase(text, "all drones")
        or _contains_word_or_phrase(text, "all drone")
        or _contains_word_or_phrase(text, "drone")
        or _contains_word_or_phrase(text, "drones")
    ):
        return "drones"

    if _contains_word_or_phrase(text, "irrigation canal"):
        return "irrigation canal"

    for canonical, aliases in TARGET_ALIASES:
        if canonical == "drones":
            continue
        if any(_contains_word_or_phrase(text, alias) for alias in aliases):
            return canonical
    return _extract_open_vocabulary_target(text, action)


def _extract_open_vocabulary_target(text: str, action: str | None) -> str | None:
    """Extract a bounded noun phrase when a target is not in the alias table."""

    if action is None or action in {"return", "hold"}:
        return None

    stop = _target_stop_pattern(include_for=action != "search")
    patterns_by_action: dict[str, tuple[str, ...]] = {
        "inspect": (
            rf"\b(?:inspect|check|survey)\s+(?:the\s+|a\s+|an\s+)?(.+?){stop}",
        ),
        "scan": (
            rf"\bscan\s+(?:the\s+|a\s+|an\s+)?(.+?){stop}",
        ),
        "capture": (
            rf"\bcapture(?:\s+images?)?(?:\s+of)?\s+(?:the\s+|a\s+|an\s+)?(.+?){stop}",
        ),
        "search": (
            rf"\bsearch\b.+?\bfor\s+(?:the\s+|a\s+|an\s+)?(.+?){_target_stop_pattern(include_for=False)}",
            rf"\bsearch\s+(?:the\s+|a\s+|an\s+)?(.+?){stop}",
        ),
    }

    for pattern in patterns_by_action.get(action, ()):
        match = re.search(pattern, text)
        if not match:
            continue
        target = _clean_open_target(match.group(1))
        if target:
            return target
    return None


def _target_stop_pattern(*, include_for: bool) -> str:
    markers = list(TARGET_STOP_MARKERS)
    if include_for:
        markers.append("for")
    marker_pattern = "|".join(re.escape(marker) for marker in markers)
    action_pattern = "|".join(
        re.escape(keyword)
        for _, keywords in ACTION_PATTERNS
        for keyword in keywords
        if keyword not in {"hold", "send", "dispatch"}
    )
    return rf"(?=\s+(?:{marker_pattern})\b|\s+and\s+(?:{action_pattern}|report)\b|$)"


def _clean_open_target(target: str) -> str | None:
    cleaned = target.strip()
    cleaned = re.sub(r"^(?:the|a|an)\s+", "", cleaned)
    cleaned = re.sub(r"\b(?:please|now)$", "", cleaned).strip()
    if not cleaned:
        return None
    if cleaned in {"drone", "drones"}:
        return None
    if cleaned in {alias for _, aliases in LOCATION_ALIASES for alias in aliases}:
        return None
    if len(cleaned.split()) > 8:
        return None
    return cleaned


def _extract_constraints(text: str) -> list[str]:
    constraints: list[str] = []
    if _contains_word_or_phrase(text, "highest battery") or _contains_word_or_phrase(text, "most battery"):
        constraints.append("highest battery")
    for match in re.finditer(r"\bkeep\s+(?:them|the\s+drones|drones)\s+below\s+([a-z0-9-]+)\s+(?:meters|metres)\b", text):
        constraints.append(f"keep them below {match.group(1)} meters")
    for match in re.finditer(r"\bbelow\s+([a-z0-9-]+)\s+(?:meters|metres)\b", text):
        altitude_constraint = f"below {match.group(1)} meters"
        if not any(altitude_constraint in constraint for constraint in constraints):
            constraints.append(altitude_constraint)
    split_match = re.search(r"\bsplit\s+(.+?)\s+into\s+(.+?)(?:\s+and\b|$)", text)
    if split_match:
        constraints.append(f"split {split_match.group(1).strip()} into {split_match.group(2).strip()}")
    divide_match = re.search(r"\bdivide\s+(.+?)\s+between\s+(.+?)(?:\s+and\b|$)", text)
    if divide_match:
        constraints.append(f"divide {divide_match.group(1).strip()} between {divide_match.group(2).strip()}")
    if re.search(r"\bone\s+drone\s+north\s+and\s+another\s+east\b", text):
        constraints.append("one drone north and another east")
    if _contains_word_or_phrase(text, "nearest drone"):
        constraints.append("nearest drone")
    for marker in ("while", "before", "after", "without", "avoid", "using"):
        match = re.search(rf"\b{marker}\b\s+(.+)$", text)
        if match:
            phrase = match.group(1).strip()
            if marker == "while" and phrase.startswith("one drone"):
                constraints.append(phrase)
            else:
                constraints.append(f"{marker} {phrase}")
    for phrase in (
        "for blocked exits",
        "for signs of dryness",
        "back to base",
        "report anything unusual",
        "report areas of heavy crowding",
        "return to base",
        "return to the launch point",
    ):
        if _contains_word_or_phrase(text, phrase):
            constraints.append(phrase)
    return constraints


def _contains_word_or_phrase(text: str, phrase: str) -> bool:
    escaped = re.escape(phrase)
    return re.search(rf"\b{escaped}\b", text) is not None
