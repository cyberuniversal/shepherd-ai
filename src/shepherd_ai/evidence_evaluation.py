"""Scoring utilities for evidence-aware mission decision experiments."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping


DECISIONS = ("proceed", "clarify", "block")


def workflow_status_to_decision(status: str) -> str:
    """Map bounded workflow statuses to a common operator-facing decision."""

    if status in {
        "ready_for_simulated_execution",
        "awaiting_required_week8_evidence",
    }:
        return "proceed"
    if status == "clarification_required":
        return "clarify"
    if status in {
        "planning_blocked",
        "scheduling_incomplete",
        "safety_blocked",
        "safety_incomplete",
        "safety_rejected",
    }:
        return "block"
    raise ValueError(f"unsupported workflow status: {status}")


def score_decision_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    expected_field: str = "expected_decision",
    predicted_field: str = "predicted_decision",
) -> dict[str, Any]:
    """Score proceed/clarify/block decisions without hiding denominators."""

    records = [dict(row) for row in rows]
    for row in records:
        _validate_decision(str(row.get(expected_field)), expected_field)
        _validate_decision(str(row.get(predicted_field)), predicted_field)

    expected_counts = Counter(str(row[expected_field]) for row in records)
    predicted_counts = Counter(str(row[predicted_field]) for row in records)
    correct = sum(row[expected_field] == row[predicted_field] for row in records)
    proceed_cases = expected_counts["proceed"]
    non_proceed_cases = len(records) - proceed_cases
    clarification_cases = expected_counts["clarify"]
    block_cases = expected_counts["block"]
    false_refusals = sum(
        row[expected_field] == "proceed" and row[predicted_field] != "proceed"
        for row in records
    )
    silent_misexecutions = sum(
        row[expected_field] != "proceed" and row[predicted_field] == "proceed"
        for row in records
    )
    clarification_hits = sum(
        row[expected_field] == "clarify" and row[predicted_field] == "clarify"
        for row in records
    )
    block_hits = sum(
        row[expected_field] == "block" and row[predicted_field] == "block"
        for row in records
    )
    return {
        "case_count": len(records),
        "correct_decisions": correct,
        "decision_accuracy": _ratio(correct, len(records)),
        "expected_decision_counts": dict(sorted(expected_counts.items())),
        "predicted_decision_counts": dict(sorted(predicted_counts.items())),
        "false_refusals": false_refusals,
        "false_refusal_denominator": proceed_cases,
        "false_refusal_rate": _ratio(false_refusals, proceed_cases),
        "silent_misexecutions": silent_misexecutions,
        "silent_misexecution_denominator": non_proceed_cases,
        "silent_misexecution_rate": _ratio(silent_misexecutions, non_proceed_cases),
        "clarification_hits": clarification_hits,
        "clarification_denominator": clarification_cases,
        "clarification_recall": _ratio(clarification_hits, clarification_cases),
        "block_hits": block_hits,
        "block_denominator": block_cases,
        "block_recall": _ratio(block_hits, block_cases),
    }


def score_clarification_recovery(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Score only cases that define a valid clarification resolution."""

    records = [dict(row) for row in rows]
    attempted = [row for row in records if row.get("recovery_attempted") is True]
    recovered = sum(row.get("recovery_succeeded") is True for row in attempted)
    return {
        "recovery_attempts": len(attempted),
        "successful_recoveries": recovered,
        "clarification_recovery_rate": _ratio(recovered, len(attempted)),
    }


def _validate_decision(value: str, field_name: str) -> None:
    if value not in DECISIONS:
        raise ValueError(f"{field_name} must be one of {DECISIONS}: {value!r}")


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None
