"""Assemble bounded intent JSON from span entities.

This module evaluates the bridge between Week 2 span extraction and the
roadmap-level intent schema. It does not run a model and does not execute a
mission; it converts human-verified or model-predicted spans into inspectable
JSON fields for analysis.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import re
from typing import Any

from shepherd_ai.intent import ACTION_PATTERNS, DETERMINISTIC_PARSER_NAME, NUMBER_WORDS, parse_intent
from shepherd_ai.intent_training import EVAL_FIELDS


Entity = tuple[str, int, int]
SUPPORTED_ACTIONS = {action for action, _ in ACTION_PATTERNS}
TARGET_REQUIRED_ACTIONS = {"capture", "inspect", "search"}
LOCATION_OR_TARGET_REQUIRED_ACTIONS = {"scan"}
LOCATION_REQUIRED_ACTIONS = {"hold", "send"}
KNOWN_SHORT_CONSTRAINTS = {
    "closest drone",
    "highest battery",
    "nearest drone",
    "strongest signal",
    "wide photo",
}


def assemble_intent_from_entities(text: str, entities: list[list[Any]] | list[tuple[Any, ...]]) -> dict[str, Any]:
    """Convert span entities into the Week 2 intent-field shape."""

    spans_by_field: dict[str, list[str]] = defaultdict(list)
    for field, start, end in (_coerce_entity(entity) for entity in entities):
        if field == "constraint":
            output_field = "constraints"
        else:
            output_field = field
        if output_field not in {"action", "count", "location", "target", "constraints"}:
            continue
        span_text = _clean_phrase(text[start:end])
        if span_text:
            spans_by_field[output_field].append(span_text)

    return {
        "action": _normalize_action(_first(spans_by_field["action"])),
        "count": _normalize_count(_first(spans_by_field["count"])),
        "location": _first(spans_by_field["location"]),
        "target": _first(spans_by_field["target"]),
        "constraints": spans_by_field["constraints"],
    }


def assemble_hybrid_intent_from_entities(text: str, entities: list[list[Any]] | list[tuple[Any, ...]]) -> dict[str, Any]:
    """Assemble intent using span boundaries first and parser fallback second.

    The trained span path is trusted for explicit entity boundaries. The
    deterministic parser is used only for fields that are absent from spans,
    and target/location fallback is intentionally conservative so parser
    guesses do not overwrite model-predicted boundaries.
    """

    span_intent = assemble_intent_from_entities(text, entities)
    span_targets = _entity_phrases(text, entities, "target")
    parser_intent = _project_intent(parse_intent(text).to_dict())
    location_from_constraint = _destination_from_selection_constraint(span_intent["constraints"])
    constraints = _clean_hybrid_constraints(text, span_intent["constraints"], span_targets)
    hybrid = {
        "action": span_intent["action"] or parser_intent["action"],
        "count": span_intent["count"] if span_intent["count"] is not None else parser_intent["count"],
        "location": span_intent["location"],
        "target": span_intent["target"],
        "constraints": constraints,
    }
    if hybrid["location"] is None and hybrid["target"] is None:
        hybrid["location"] = parser_intent["location"]
        hybrid["target"] = parser_intent["target"]
    if hybrid["location"] is None and location_from_constraint:
        if hybrid["target"] == location_from_constraint:
            hybrid["target"] = None
        hybrid["location"] = location_from_constraint
    hybrid = _repair_split_location_target(text, hybrid, parser_intent)
    return hybrid


def validate_assembled_intent(intent: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic validation issues for an assembled intent."""

    issues: list[dict[str, str]] = []
    action = intent.get("action")
    count = intent.get("count")
    constraints = intent.get("constraints")

    if action is None:
        issues.append(_issue("error", "action", "missing_action", "intent action is required"))
    elif action not in SUPPORTED_ACTIONS:
        issues.append(_issue("error", "action", "unsupported_action", f"unsupported action: {action}"))

    if count is not None and not (count == "all" or isinstance(count, int)):
        issues.append(_issue("error", "count", "invalid_count", "count must be an integer, 'all', or null"))

    if not isinstance(constraints, list):
        issues.append(_issue("error", "constraints", "invalid_constraints", "constraints must be a list"))
        constraints = []

    if action in TARGET_REQUIRED_ACTIONS and not intent.get("target"):
        issues.append(
            _issue("error", "target", "missing_required_target", f"{action} intent requires a target")
        )
    if action in LOCATION_OR_TARGET_REQUIRED_ACTIONS and not intent.get("location") and not intent.get("target"):
        issues.append(
            _issue("error", "target", "missing_scan_grounding_phrase", "scan intent requires location or target")
        )
    if action in LOCATION_REQUIRED_ACTIONS and not intent.get("location"):
        issues.append(
            _issue("warning", "location", "missing_expected_location", f"{action} intent usually needs a location")
        )

    for constraint in constraints:
        constraint_text = str(constraint).strip()
        if not constraint_text:
            issues.append(_issue("warning", "constraints", "empty_constraint", "empty constraint span"))
            continue
        if _is_suspicious_short_constraint(constraint_text):
            issues.append(
                _issue(
                    "warning",
                    "constraints",
                    "suspicious_short_constraint",
                    f"single-token constraint is suspicious: {constraint_text}",
                )
            )

    severity_counts = Counter(issue["severity"] for issue in issues)
    return {
        "valid": severity_counts.get("error", 0) == 0,
        "issues": issues,
        "issue_counts": dict(sorted(severity_counts.items())),
    }


def evaluate_span_intent_assembly(
    evaluation: dict[str, Any],
    *,
    model_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate expected-vs-predicted span entities after intent assembly."""

    rows: list[dict[str, Any]] = []
    for record in evaluation.get("records", []):
        text = str(record.get("text", ""))
        expected_intent = assemble_intent_from_entities(text, record.get("expected_entities", []))
        predicted_intent = assemble_intent_from_entities(text, record.get("predicted_entities", []))
        expected_validation = validate_assembled_intent(expected_intent)
        predicted_validation = validate_assembled_intent(predicted_intent)
        field_matches = {
            field: expected_intent.get(field) == predicted_intent.get(field)
            for field in EVAL_FIELDS
        }
        rows.append(
            {
                "id": str(record.get("id")),
                "split": record.get("split"),
                "text": text,
                "expected_intent": expected_intent,
                "predicted_intent": predicted_intent,
                "expected_validation": expected_validation,
                "predicted_validation": predicted_validation,
                "field_matches": field_matches,
                "all_fields_match": all(field_matches.values()),
                "expected_entities": record.get("expected_entities", []),
                "predicted_entities": record.get("predicted_entities", []),
            }
        )

    source_metadata = evaluation.get("metadata", {})
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_model": model_name or source_metadata.get("model_name", "not stated"),
            "source_dataset": source_metadata.get("dataset", "not stated"),
            "source_evaluation_note": source_metadata.get("note", "not stated"),
            "note": (
                "Span-to-intent assembly evaluation. Expected intent is derived from human-verified "
                "expected span entities, and predicted intent is derived from model-predicted span "
                "entities. This is not ASR evaluation and not end-to-end mission success."
            ),
            **(metadata or {}),
        },
        "summary": _summarize(rows),
        "records": rows,
    }


def compare_intent_paths_from_span_evaluation(
    evaluation: dict[str, Any],
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare parser and span-assembled intent paths on the same span records."""

    rows: list[dict[str, Any]] = []
    for record in evaluation.get("records", []):
        text = str(record.get("text", ""))
        expected_intent = assemble_intent_from_entities(text, record.get("expected_entities", []))
        systems = {
            DETERMINISTIC_PARSER_NAME: _project_intent(parse_intent(text).to_dict()),
            "span_intent_assembly": assemble_intent_from_entities(text, record.get("predicted_entities", [])),
            "hybrid_span_parser": assemble_hybrid_intent_from_entities(text, record.get("predicted_entities", [])),
        }
        for system_name, predicted_intent in systems.items():
            validation = validate_assembled_intent(predicted_intent)
            field_matches = {
                field: expected_intent.get(field) == predicted_intent.get(field)
                for field in EVAL_FIELDS
            }
            rows.append(
                {
                    "id": str(record.get("id")),
                    "split": record.get("split"),
                    "text": text,
                    "system": system_name,
                    "expected_intent": expected_intent,
                    "predicted_intent": predicted_intent,
                    "predicted_validation": validation,
                    "field_matches": field_matches,
                    "all_fields_match": all(field_matches.values()),
                }
            )

    source_metadata = evaluation.get("metadata", {})
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_model": source_metadata.get("model_name", "not stated"),
            "source_dataset": source_metadata.get("dataset", "not stated"),
            "note": (
                "Comparison of deterministic parser and trained span-to-intent assembly on the same "
                "span-evaluation records. Expected intent is derived from human-verified span entities."
            ),
            **(metadata or {}),
        },
        "summary": _summarize_by_system(rows),
        "records": rows,
    }


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    field_matches = 0
    total_fields = 0
    field_error_counts: Counter[str] = Counter()
    predicted_validation_issue_counts: Counter[str] = Counter()
    predicted_validation_field_counts: Counter[str] = Counter()
    split_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        split = str(row.get("split", "not stated"))
        split_counts[split]["records"] += 1
        if row["all_fields_match"]:
            split_counts[split]["exact_record_matches"] += 1
        for field, matched in row["field_matches"].items():
            total_fields += 1
            if matched:
                field_matches += 1
            else:
                field_error_counts[field] += 1
        predicted_issues = row.get("predicted_validation", {}).get("issues", [])
        if any(issue.get("severity") == "error" for issue in predicted_issues):
            split_counts[split]["records_with_validation_errors"] += 1
        if predicted_issues:
            split_counts[split]["records_with_validation_issues"] += 1
        for issue in predicted_issues:
            predicted_validation_issue_counts[str(issue.get("code"))] += 1
            predicted_validation_field_counts[str(issue.get("field"))] += 1
    exact_matches = sum(1 for row in rows if row["all_fields_match"])
    return {
        "records": len(rows),
        "exact_record_matches": exact_matches,
        "exact_record_accuracy": exact_matches / len(rows) if rows else 0.0,
        "field_matches": field_matches,
        "total_fields": total_fields,
        "field_accuracy": field_matches / total_fields if total_fields else 0.0,
        "field_error_counts": dict(sorted(field_error_counts.items())),
        "predicted_validation_issue_counts": dict(sorted(predicted_validation_issue_counts.items())),
        "predicted_validation_field_counts": dict(sorted(predicted_validation_field_counts.items())),
        "records_with_predicted_validation_errors": sum(
            1
            for row in rows
            if any(issue.get("severity") == "error" for issue in row.get("predicted_validation", {}).get("issues", []))
        ),
        "records_with_predicted_validation_issues": sum(
            1 for row in rows if row.get("predicted_validation", {}).get("issues")
        ),
        "split_counts": {split: dict(counts) for split, counts in sorted(split_counts.items())},
    }


def _summarize_by_system(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["system"])].append(row)
    return {system: _summarize(system_rows) for system, system_rows in sorted(grouped.items())}


def _project_intent(intent: dict[str, Any]) -> dict[str, Any]:
    return {field: intent.get(field) for field in EVAL_FIELDS}


def _is_suspicious_short_constraint(constraint: str) -> bool:
    constraint_text = str(constraint).strip()
    return len(constraint_text.split()) == 1 and constraint_text not in KNOWN_SHORT_CONSTRAINTS


def _clean_hybrid_constraints(text: str, constraints: list[str], span_targets: list[str]) -> list[str]:
    cleaned: list[str] = []
    for constraint in constraints:
        if _is_suspicious_short_constraint(constraint):
            continue
        if _is_drone_selection_constraint(constraint):
            continue
        cleaned.append(constraint)

    text_lower = text.lower()
    if "into equal sections" in text_lower and {"sections", "equal sections"}.intersection(span_targets):
        if "into equal sections" not in cleaned:
            cleaned.append("into equal sections")
    return cleaned


def _is_drone_selection_constraint(constraint: str) -> bool:
    constraint_text = _clean_phrase(constraint)
    return bool(re.search(r"\b(?:highest|most)\s+battery\b", constraint_text))


def _destination_from_selection_constraint(constraints: list[str]) -> str | None:
    for constraint in constraints:
        if not _is_drone_selection_constraint(constraint):
            continue
        destination_match = re.search(r"\bto\s+(?:the\s+)?(.+)$", constraint.strip(), flags=re.IGNORECASE)
        if destination_match:
            return _clean_phrase(destination_match.group(1))
    return None


def _repair_split_location_target(text: str, intent: dict[str, Any], parser_intent: dict[str, Any]) -> dict[str, Any]:
    location = intent.get("location")
    target = intent.get("target")
    if not isinstance(location, str) or not isinstance(target, str):
        return intent
    combined = _clean_phrase(f"{location} {target}")
    if combined and combined == parser_intent.get("location") and re.search(rf"\b{re.escape(combined)}\b", text.lower()):
        repaired = dict(intent)
        repaired["location"] = None
        repaired["target"] = combined
        return repaired
    return intent


def _entity_phrases(text: str, entities: list[list[Any]] | list[tuple[Any, ...]], field_name: str) -> list[str]:
    phrases: list[str] = []
    for field, start, end in (_coerce_entity(entity) for entity in entities):
        if field == field_name:
            phrase = _clean_phrase(text[start:end])
            if phrase:
                phrases.append(phrase)
    return phrases


def _issue(severity: str, field: str, code: str, message: str) -> dict[str, str]:
    return {"severity": severity, "field": field, "code": code, "message": message}


def _coerce_entity(entity: list[Any] | tuple[Any, ...]) -> Entity:
    if len(entity) != 3:
        raise ValueError(f"entity must have field, start, and end: {entity!r}")
    field, start, end = entity
    return str(field), int(start), int(end)


def _first(values: list[str]) -> str | None:
    return values[0] if values else None


def _clean_phrase(text: str) -> str:
    cleaned = text.strip().lower()
    cleaned = re.sub(r"^(?:the|a|an)\s+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" .,;:")


def _normalize_action(action: str | None) -> str | None:
    if action is None:
        return None
    action_text = _clean_phrase(action)
    for canonical, keywords in ACTION_PATTERNS:
        if any(re.search(rf"\b{re.escape(keyword)}\b", action_text) for keyword in keywords):
            return canonical
    return action_text or None


def _normalize_count(count: str | None) -> int | str | None:
    if count is None:
        return None
    count_text = _clean_phrase(count)
    if "all" in count_text or "every" in count_text:
        return "all"
    digit_match = re.search(r"\b(\d+)\b", count_text)
    if digit_match:
        value = int(digit_match.group(1))
        return 1 if re.search(r"\bdrone\s+\d+\b", count_text) else value
    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", count_text):
            return 1 if re.search(rf"\bdrone\s+{word}\b", count_text) else value
    if "drone" in count_text:
        return 1
    return None
