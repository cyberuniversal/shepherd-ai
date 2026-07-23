"""Prompt and output contracts for a monolithic mission-decision baseline."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from shepherd_ai.evidence_evaluation import DECISIONS


PROMPT_VERSION = "shepherd_monolithic_decision_prompt_v1"
SYSTEM_PROMPT = """You are a single-stage multi-drone mission decision system.
Use only the supplied command and evidence. Choose exactly one decision:
- proceed: the current stage has sufficient, consistent evidence to advance;
- clarify: operator input is required to resolve ambiguity, missing references, or conflicts;
- block: the mission violates the supplied policy or cannot safely advance.

Do not invent locations, drone state, policy values, or observations. Return one
JSON object with keys decision, reason, and clarification_question. The decision
must be proceed, clarify, or block. Use null for clarification_question unless
the decision is clarify. Do not include Markdown or additional text."""


def build_messages(record: Mapping[str, Any]) -> list[dict[str, str]]:
    """Build the exact model messages without exposing gold labels."""

    required = ("case_id", "decision_stage", "command", "evidence")
    missing = [field for field in required if field not in record]
    if missing:
        raise ValueError(f"baseline input is missing: {', '.join(missing)}")
    evidence = record["evidence"]
    if not isinstance(evidence, Mapping):
        raise ValueError("baseline evidence must be an object")
    user_payload = {
        "case_id": str(record["case_id"]),
        "decision_stage": str(record["decision_stage"]),
        "stage_definition": str(record.get("stage_definition", "")),
        "command": str(record["command"]),
        "evidence": dict(evidence),
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                user_payload,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
        },
    ]


def messages_sha256(messages: list[dict[str, str]]) -> str:
    encoded = json.dumps(
        messages,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parse_model_response(text: str) -> dict[str, Any]:
    """Parse one strict JSON response; malformed output remains invalid."""

    cleaned = text.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3 and lines[0].strip().lower() in {"```", "```json"}:
            cleaned = "\n".join(lines[1:-1]).strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as error:
        return {
            "valid": False,
            "decision": None,
            "reason": None,
            "clarification_question": None,
            "error": f"invalid_json: {error.msg}",
        }
    if not isinstance(payload, dict):
        return _invalid("response_must_be_object")
    decision = payload.get("decision")
    reason = payload.get("reason")
    question = payload.get("clarification_question")
    if decision not in DECISIONS:
        return _invalid("decision_must_be_proceed_clarify_or_block")
    if not isinstance(reason, str) or not reason.strip():
        return _invalid("reason_must_be_nonempty_string")
    if decision == "clarify":
        if not isinstance(question, str) or not question.strip():
            return _invalid("clarify_requires_question")
    elif question is not None:
        return _invalid("non_clarify_question_must_be_null")
    return {
        "valid": True,
        "decision": decision,
        "reason": reason.strip(),
        "clarification_question": question.strip() if isinstance(question, str) else None,
        "error": None,
    }


def validate_input_record(record: Mapping[str, Any]) -> None:
    messages = record.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("baseline input requires non-empty messages")
    expected_hash = messages_sha256(messages)
    if record.get("prompt_sha256") != expected_hash:
        raise ValueError(f"{record.get('case_id', 'unknown')}: prompt hash mismatch")
    forbidden = {"expected_decision", "shepherd_decision", "gold_label"}
    if forbidden & set(record):
        raise ValueError(
            f"{record.get('case_id', 'unknown')}: input packet contains gold fields"
        )


def _invalid(error: str) -> dict[str, Any]:
    return {
        "valid": False,
        "decision": None,
        "reason": None,
        "clarification_question": None,
        "error": error,
    }
