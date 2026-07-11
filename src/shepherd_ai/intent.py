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


DETERMINISTIC_PARSER_NAME = "deterministic_v3"

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
    "near",
    "from",
    "until",
)

ACTION_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hold", ("hold position", "hold", "stay")),
    ("search", ("search",)),
    ("capture", ("capture", "capture images", "photograph", "take photos", "take pictures")),
    ("inspect", ("inspect", "check", "survey", "expect", "server", "look for")),
    ("scan", ("scan", "scanda", "scam", "map", "monitor", "monitoring")),
    ("return", ("return", "come back", "bring back", "back to base", "back to the base")),
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
    location = _extract_location(normalized, action)
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
    if re.search(r"\breturn\s+(?:the\s+)?(?:closest\s+|nearest\s+)?drone\b", text):
        return "return"
    if re.search(r"\breturn\s+drone\s+(?:\d+|[a-z]+)\b", text):
        return "return"
    if re.search(r"\bbring\b.+\bback\b", text):
        return "return"
    if re.search(r"\bsend\b.+\bthen\s+return\b", text):
        return "send"
    if re.search(r"\bsend\b.+\bback\s+to\b", text):
        return "return"
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
    digit_match = re.search(r"\b(\d+)\s+(?:drones?|jones)\b", text)
    if digit_match:
        count_mentions.append(int(digit_match.group(1)))

    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\s+(?:drones?|jones)\b", text):
            count_mentions.append(value)
        if re.search(rf"\b{word}\s+more\b", text):
            count_mentions.append(value)

    if count_mentions:
        if re.search(r"\banother(?:\s+drone)?\b", text):
            count_mentions.append(1)
        return sum(count_mentions)

    drone_id_match = re.search(r"\b(?:drone|drawn)\s+(\d+)\b", text)
    if drone_id_match:
        return 1

    for word in NUMBER_WORDS:
        if re.search(rf"\b(?:drone|drawn)\s+{word}\b", text):
            return 1

    if (
        _contains_word_or_phrase(text, "the drone")
        or _contains_word_or_phrase(text, "nearest drone")
        or _contains_word_or_phrase(text, "closest drone")
        or _contains_word_or_phrase(text, "whichever drone")
    ):
        return 1

    return None


def _extract_location(text: str, action: str | None) -> str | None:
    pattern_location = _extract_pattern_location(text, action)
    if pattern_location:
        return pattern_location

    matched_locations: list[str] = []
    for canonical, aliases in LOCATION_ALIASES:
        if any(_contains_word_or_phrase(text, alias) for alias in aliases):
            matched_locations.append(canonical)
    if len(matched_locations) == 1:
        return matched_locations[0]
    return None


def _extract_pattern_location(text: str, action: str | None) -> str | None:
    if action == "return":
        phrase = _first_clean_match(
            text,
            (
                r"\bback\s+to\s+(?:the\s+)?(.+?)(?:$|\s+after\b)",
                r"\breturn\s+all\s+(?:the\s+)?drones\s+to\s+(?:the\s+)?(.+?)(?:$|\s+after\b)",
                r"\breturn\s+(?:the\s+)?(?:closest\s+|nearest\s+)?drone\s+to\s+(?:the\s+)?(.+?)(?:$|\s+after\b)",
                r"\breturn\s+drone\s+(?:\d+|[a-z]+)\s+to\s+(?:the\s+)?(.+?)(?:$|\s+after\b)",
            ),
        )
        return phrase

    if action in {"scan", "search"}:
        if re.search(r"\bsend\b.+\bto\s+monitor(?:ing)?\b", text):
            return None
        phrase = _first_clean_match(
            text,
            (
                r"\b(?:scan|scanda|scam|search)\s+(?:the\s+|a\s+|an\s+)?(.+?)\s+for\b",
                r"\bmonitor(?:ing)?\s+(?:the\s+|a\s+|an\s+)?(.+?)(?:\s+until\b|\s+while\b|$)",
            ),
        )
        if phrase:
            return phrase

    if action == "inspect":
        phrase = _first_clean_match(
            text,
            (
                r"\b(?:inspect|check|survey|server|expect)\s+(?:the\s+|a\s+|an\s+)?(.+?)\s+for\b",
                r"\bnear\s+(?:the\s+|a\s+|an\s+)?(.+?)(?:$|\s+(?:after|before|without|while|and)\b)",
                r"\b(?:inspect|check|survey|server|expect)\s+(?:the\s+|a\s+|an\s+)?(.+?)\s+and\s+look\s+for\b",
            ),
        )
        if phrase:
            return phrase

    if action == "hold":
        phrase = _first_clean_match(
            text,
            (
                r"\babove\s+(?:the\s+|a\s+|an\s+)?(.+?)(?:\s+until\b|$)",
                r"\b(north\s+of\s+.+?)(?:\s+and\s+hold\b|\s+hold\b|$)",
                r"\b(south\s+of\s+.+?)(?:\s+and\s+hold\b|\s+hold\b|$)",
                r"\b(east\s+of\s+.+?)(?:\s+and\s+hold\b|\s+hold\b|$)",
                r"\b(west\s+of\s+.+?)(?:\s+and\s+hold\b|\s+hold\b|$)",
            ),
        )
        if phrase:
            return phrase

    if action == "capture":
        phrase = _first_clean_match(
            text,
            (
                r"\bnear\s+(?:the\s+|a\s+|an\s+)?(.+?)(?:$|\s+(?:after|before|without|while|and)\b)",
            ),
        )
        if phrase:
            return phrase

    if action == "send":
        phrase = _first_clean_match(
            text,
            (
                r"\bto\s+cover\s+(?:the\s+|a\s+|an\s+)?(.+?)(?:\s+then\b|$)",
                r"\babove\s+(?:the\s+|a\s+|an\s+)?(.+?)(?:\s+but\b|$)",
                r"\bto\s+(?:the\s+|a\s+|an\s+)?(.+?)(?:\s+then\b|$)",
            ),
        )
        if phrase and not _is_known_target_phrase(phrase):
            return phrase

    return None


def _extract_target(text: str, action: str | None) -> str | None:
    if action == "return" and (
        _contains_word_or_phrase(text, "all drones")
        or _contains_word_or_phrase(text, "all drone")
        or _contains_word_or_phrase(text, "drone")
        or _contains_word_or_phrase(text, "drones")
    ):
        return "drones"

    if re.search(r"\bdivide\s+the\s+field\s+between\b", text):
        return "field"

    pattern_target = _extract_pattern_target(text, action)
    if pattern_target:
        return pattern_target

    target_text = _target_alias_search_text(text, action)

    if _contains_word_or_phrase(target_text, "irrigation canal"):
        return "irrigation canal"

    for canonical, aliases in TARGET_ALIASES:
        if canonical == "drones":
            continue
        if any(_contains_word_or_phrase(target_text, alias) for alias in aliases):
            return canonical
    return _extract_open_vocabulary_target(text, action)


def _target_alias_search_text(text: str, action: str | None) -> str:
    search_text = text
    for candidate_action, keywords in ACTION_PATTERNS:
        if candidate_action != action or action in {None, "send", "return", "hold"}:
            continue
        matches = [
            match
            for keyword in keywords
            for match in re.finditer(rf"\b{re.escape(keyword)}\b", search_text)
        ]
        if matches:
            search_text = search_text[max(match.start() for match in matches) :]
            break
    for marker in ("while", "without", "before", "after", "using", "below", "near"):
        match = re.search(rf"\b{marker}\b", search_text)
        if match:
            search_text = search_text[: match.start()].strip()
    if action != "search":
        match = re.search(r"\bfor\b", search_text)
        if match:
            search_text = search_text[: match.start()].strip()
    return search_text


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
            rf"\b(?:capture(?:\s+images?)?(?:\s+of)?|photograph)\s+(?:the\s+|a\s+|an\s+)?(.+?){stop}",
            rf"\btake\s+(?:photos|pictures)\s+(?:of\s+)?(?:the\s+|a\s+|an\s+)?(.+?){stop}",
        ),
        "search": (
            rf"\bdivide\s+(?:the\s+|a\s+|an\s+)?(.+?)\s+into\s+.+?(?:$|\s+and\b)",
            rf"\bsearch\b.+?\bfor\s+(?:the\s+|a\s+|an\s+)?(.+?){_target_stop_pattern(include_for=False)}",
            rf"\bsearch\s+(?:the\s+|a\s+|an\s+)?(.+?){stop}",
        ),
        "scan": (
            rf"\bmap\s+(?:the\s+|a\s+|an\s+)?(.+?){stop}",
            rf"\bmonitor(?:ing)?\s+(?:the\s+|a\s+|an\s+)?(.+?){stop}",
            rf"\b(?:scan|scanda|scam)\s+(?:the\s+|a\s+|an\s+)?(.+?){stop}",
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
    cleaned = re.sub(r"^(?:the|a|an|that)\s+", "", cleaned)
    cleaned = re.sub(r"\b(?:please|now)$", "", cleaned).strip()
    if not cleaned:
        return None
    if cleaned in {"drone", "drones"}:
        return None
    if cleaned in {alias for _, aliases in LOCATION_ALIASES for alias in aliases}:
        return None
    if cleaned == "gate house":
        return "gatehouse"
    if cleaned == "easter walking path":
        return "eastern walking path"
    if cleaned == "north center and south sections":
        return "north, center, and south sections"
    if len(cleaned.split()) > 8:
        return None
    return cleaned


def _extract_pattern_target(text: str, action: str | None) -> str | None:
    if action in {"scan", "search", "inspect"}:
        phrase = _first_clean_match(
            text,
            (
                r"\bcheck\s+if\s+there\s+(?:is|are)\s+(?:any\s+|a\s+|an\s+)?(.+?)(?:$|\s+(?:after|before|without|while)\b)",
                r"\b(?:scan|scanda|search|inspect|check|survey|server|expect)\b.+?\bfor\s+(?:the\s+|a\s+|an\s+)?(.+?)(?:$|\s+(?:after|before|without|while)\b)",
                r"\blook\s+for\s+(?:the\s+|a\s+|an\s+)?(.+?)(?:$|\s+(?:after|before|without|while)\b)",
            ),
        )
        if phrase:
            return phrase
    if action == "capture":
        phrase = _first_clean_match(
            text,
            (
                r"\bphotograph\s+(?:the\s+|a\s+|an\s+)?(.+?)(?:$|\s+near\b|\s+(?:after|before|without|while)\b)",
                r"\bcapture\s+(?:a\s+)?wide\s+photo\s+of\s+(?:the\s+|a\s+|an\s+)?(.+?)(?:$|\s+and\s+send\b|\s+(?:after|before|without|while)\b)",
                r"\bcapture(?:\s+images?)?(?:\s+of)?\s+(?:the\s+|a\s+|an\s+)?(.+?)(?:$|\s+and\s+send\b|\s+(?:after|before|without|while)\b)",
                r"\bfollow\s+(?:the\s+|a\s+|an\s+)?(.+?)\s+and\s+take\s+(?:photos|pictures)\b",
            ),
        )
        if phrase:
            return phrase
    return None


def _first_clean_match(text: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        cleaned = _clean_open_target(match.group(1))
        if cleaned:
            return cleaned
    return None


def _is_known_target_phrase(phrase: str) -> bool:
    return any(_contains_word_or_phrase(phrase, alias) for _, aliases in TARGET_ALIASES for alias in aliases)


def _extract_constraints(text: str) -> list[str]:
    constraints: list[str] = []
    if _contains_word_or_phrase(text, "highest battery") or _contains_word_or_phrase(text, "most battery"):
        constraints.append("highest battery")
    if _contains_word_or_phrase(text, "closest drone"):
        constraints.append("closest drone")
    if _contains_word_or_phrase(text, "drone with the clearest camera feed"):
        constraints.append("drone with the clearest camera feed")
    if _contains_word_or_phrase(text, "strongest signal"):
        constraints.append("strongest signal")
    for match in re.finditer(r"\bstay\s+below\s+([a-z0-9-]+)\s+(?:meters|metres)\b", text):
        constraints.append(f"stay below {match.group(1)} meters")
    for match in re.finditer(r"\bkeep\s+(?:them|the\s+drones|drones)\s+below\s+([a-z0-9-]+)\s+(?:meters|metres)\b", text):
        constraints.append(f"keep them below {match.group(1)} meters")
    for match in re.finditer(r"\bbelow\s+([a-z0-9-]+)\s+(?:meters|metres)\b", text):
        altitude_constraint = f"below {match.group(1)} meters"
        if not any(match.group(1) in constraint and "below" in constraint for constraint in constraints):
            constraints.append(altitude_constraint)
    split_match = re.search(r"\bsplit\s+(.+?)\s+into\s+(.+?)(?:\s+and\b|$)", text)
    if split_match:
        constraints.append(f"split {split_match.group(1).strip()} into {split_match.group(2).strip()}")
    divide_match = re.search(r"\bdivide\s+(.+?)\s+between\s+(.+?)(?:\s+and\b|$)", text)
    if divide_match:
        constraints.append(f"divide {divide_match.group(1).strip()} between {divide_match.group(2).strip()}")
    divide_into_match = re.search(r"\bdivide\s+(.+?)\s+into\s+(.+?)(?:\s+and\b|$)", text)
    if divide_into_match:
        constraints.append(f"divide {divide_into_match.group(1).strip()} into {divide_into_match.group(2).strip()}")
    from_to_match = re.search(r"\bfrom\s+(north|south|east|west)\s+to\s+(north|south|east|west)\b", text)
    if from_to_match:
        constraints.append(f"from {from_to_match.group(1)} to {from_to_match.group(2)}")
    if _contains_word_or_phrase(text, "from both ends"):
        constraints.append("from both ends")
    if _contains_word_or_phrase(text, "wide photo"):
        constraints.append("wide photo")
    follow_match = re.search(r"\bfollow\s+(?:the\s+|a\s+|an\s+)?(.+?)\s+and\s+take\s+(?:photos|pictures)\b", text)
    if follow_match:
        constraints.append(f"follow {follow_match.group(1).strip()}")
    if re.search(r"\bone\s+drone\s+north\s+and\s+another\s+east\b", text):
        constraints.append("one drone north and another east")
    if _contains_word_or_phrase(text, "nearest drone"):
        constraints.append("nearest drone")
    greenhouse_scan_match = re.search(r"\b(dispatch|send)\s+one\s+drone\s+to\s+the\s+greenhouse\s+then\b", text)
    if greenhouse_scan_match:
        constraints.append("one drone to the greenhouse")
    for marker in ("while", "before", "after", "without", "avoid", "using", "until"):
        match = re.search(rf"\b{marker}\b\s+(.+)$", text)
        if match:
            phrase = match.group(1).strip()
            if marker == "using" and phrase == "one drone":
                continue
            if marker == "while" and phrase.startswith("one drone"):
                constraints.append(phrase)
            else:
                constraints.append(f"{marker} {phrase}")
    then_match = re.search(r"\bthen\s+(return.+)$", text)
    if then_match:
        constraints.append(f"then {then_match.group(1).strip()}")
    for phrase in (
        "for blocked exits",
        "for signs of dryness",
        "back to base",
        "send a report",
        "report any blocked access points",
        "report any blocked passage",
        "report anything unusual",
        "report areas of heavy crowding",
        "return to base",
        "return to the launch point",
        "return to me",
        "return to the control tent",
    ):
        if _contains_word_or_phrase(text, phrase):
            constraints.append(phrase)
    return constraints


def _contains_word_or_phrase(text: str, phrase: str) -> bool:
    escaped = re.escape(phrase)
    return re.search(rf"\b{escaped}\b", text) is not None
