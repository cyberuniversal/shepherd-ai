"""Span-labeled command utilities for Week 2 intent extraction.

This module prepares Shepherd-AI for supervised slot extraction without
requiring spaCy or Hugging Face dependencies yet. It validates exact character
spans and converts them into BIO token labels that later training code can
consume.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Any, Iterable


ALLOWED_SPAN_FIELDS = {"action", "count", "location", "target", "constraint"}
VALID_SPLITS = {"train", "validation", "test"}
TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class IntentSpan:
    field: str
    start: int
    end: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "start": self.start,
            "end": self.end,
            "text": self.text,
        }


@dataclass(frozen=True)
class SpanLabeledCommand:
    id: str
    text: str
    split: str
    source: str
    data_type: str
    spans: list[IntentSpan]
    expected_intent: dict[str, Any] | None = None


def load_span_labeled_commands(path: str | Path) -> list[SpanLabeledCommand]:
    """Load and validate a JSONL command dataset with character spans."""

    records: list[SpanLabeledCommand] = []
    input_path = Path(path)
    for line_number, line in enumerate(input_path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        records.append(_parse_span_record(raw, line_number=line_number))
    return records


def tokenize_with_offsets(text: str) -> list[Token]:
    """Return tokens with exact character offsets."""

    return [Token(match.group(0), match.start(), match.end()) for match in TOKEN_PATTERN.finditer(text)]


def spans_to_bio_tags(text: str, spans: Iterable[IntentSpan | dict[str, Any]]) -> list[tuple[Token, str]]:
    """Convert character spans into BIO tags over token offsets."""

    parsed_spans = [_coerce_span(span, text=text, line_number=1) for span in spans]
    _validate_non_overlapping_spans(parsed_spans, line_number=1)
    tagged: list[tuple[Token, str]] = []
    for token in tokenize_with_offsets(text):
        matching_spans = [span for span in parsed_spans if _token_overlaps_span(token, span)]
        if len(matching_spans) > 1:
            raise ValueError(f"token overlaps multiple spans: {token.text}")
        if not matching_spans:
            tagged.append((token, "O"))
            continue
        span = matching_spans[0]
        prefix = "B" if token.start == span.start else "I"
        tagged.append((token, f"{prefix}-{span.field}"))
    return tagged


def build_spans_from_phrases(text: str, field_phrases: Iterable[tuple[str, str]]) -> list[dict[str, Any]]:
    """Build sorted span dictionaries from exact field/phrase pairs."""

    spans: list[dict[str, Any]] = []
    for field, phrase in field_phrases:
        span_text = phrase.strip()
        if not span_text:
            continue
        start, end = unique_phrase_offsets(text, span_text)
        spans.append({"field": field, "start": start, "end": end, "text": text[start:end]})
    return sorted(spans, key=lambda span: (span["start"], span["end"], span["field"]))


def unique_phrase_offsets(text: str, phrase: str) -> tuple[int, int]:
    """Return offsets for a phrase that appears exactly once in text."""

    starts = _find_phrase_starts(text, phrase)
    if not starts:
        starts = _find_phrase_starts(text.lower(), phrase.lower())
    if not starts:
        raise ValueError(f"span phrase not found in command text: {phrase!r}")
    if len(starts) > 1:
        raise ValueError(f"span phrase {phrase!r} appears {len(starts)} times; use a unique exact phrase")
    return starts[0], starts[0] + len(phrase)


def _find_phrase_starts(text: str, phrase: str) -> list[int]:
    starts: list[int] = []
    start = text.find(phrase)
    while start != -1:
        starts.append(start)
        start = text.find(phrase, start + 1)
    return starts


def summarize_span_labeled_commands(records: list[SpanLabeledCommand]) -> dict[str, Any]:
    """Summarize provenance and label coverage for span-labeled commands."""

    split_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    data_type_counts: Counter[str] = Counter()
    span_field_counts: Counter[str] = Counter()
    for record in records:
        split_counts[record.split] += 1
        source_counts[record.source] += 1
        data_type_counts[record.data_type] += 1
        for span in record.spans:
            span_field_counts[span.field] += 1
    return {
        "records": len(records),
        "split_counts": dict(sorted(split_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "data_type_counts": dict(sorted(data_type_counts.items())),
        "span_field_counts": dict(sorted(span_field_counts.items())),
    }


def _parse_span_record(raw: dict[str, Any], *, line_number: int) -> SpanLabeledCommand:
    text = _required_text(raw.get("text"), "text", line_number)
    split = _required_text(raw.get("split"), "split", line_number)
    if split not in VALID_SPLITS:
        raise ValueError(f"line {line_number}: split must be one of {sorted(VALID_SPLITS)}")
    spans = [_coerce_span(span, text=text, line_number=line_number) for span in raw.get("spans", [])]
    _validate_non_overlapping_spans(spans, line_number=line_number)
    return SpanLabeledCommand(
        id=_required_text(raw.get("id"), "id", line_number),
        text=text,
        split=split,
        source=_required_text(raw.get("source"), "source", line_number),
        data_type=_required_text(raw.get("data_type"), "data_type", line_number),
        spans=spans,
        expected_intent=raw.get("expected_intent"),
    )


def _coerce_span(raw: IntentSpan | dict[str, Any], *, text: str, line_number: int) -> IntentSpan:
    if isinstance(raw, IntentSpan):
        span = raw
    else:
        field = _required_text(raw.get("field"), "field", line_number)
        start = _required_int(raw.get("start"), "start", line_number)
        end = _required_int(raw.get("end"), "end", line_number)
        span_text = _required_text(raw.get("text"), "span.text", line_number)
        span = IntentSpan(field=field, start=start, end=end, text=span_text)
    if span.field not in ALLOWED_SPAN_FIELDS:
        raise ValueError(f"line {line_number}: unsupported span field {span.field!r}")
    if span.start < 0 or span.end <= span.start or span.end > len(text):
        raise ValueError(f"line {line_number}: invalid span offsets for {span.field}")
    actual = text[span.start : span.end]
    if actual != span.text:
        raise ValueError(
            f"line {line_number}: span text mismatch for {span.field}: expected {span.text!r}, got {actual!r}"
        )
    return span


def _validate_non_overlapping_spans(spans: list[IntentSpan], *, line_number: int) -> None:
    sorted_spans = sorted(spans, key=lambda span: (span.start, span.end))
    for previous, current in zip(sorted_spans, sorted_spans[1:]):
        if current.start < previous.end:
            raise ValueError(
                f"line {line_number}: spans overlap: {previous.field} {previous.start}:{previous.end} and "
                f"{current.field} {current.start}:{current.end}"
            )


def _token_overlaps_span(token: Token, span: IntentSpan) -> bool:
    return token.start < span.end and token.end > span.start


def _required_text(value: Any, field_name: str, line_number: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"line {line_number}: {field_name} must be a non-empty string")
    return value


def _required_int(value: Any, field_name: str, line_number: int) -> int:
    if not isinstance(value, int):
        raise ValueError(f"line {line_number}: {field_name} must be an integer")
    return value
