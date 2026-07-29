"""Strict M3 evidence-ledger parsing and deterministic pre-plan checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from typing import Any, Mapping

from shepherd_ai.multiuav_context import (
    PRIVILEGED_SOURCE_FIELDS,
    validate_agent_visible_context,
)


LEDGER_FIELDS = frozenset(
    {
        "evidence",
        "missing_operator_facts",
        "conflicts",
        "provisional_decision",
        "reason",
    }
)
EVIDENCE_FIELDS = frozenset({"source_path", "claim"})
PROVISIONAL_DECISIONS = frozenset({"EXECUTE", "CLARIFY", "BLOCK"})


@dataclass(frozen=True)
class EvidenceItem:
    source_path: str
    claim: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceLedger:
    evidence: tuple[EvidenceItem, ...]
    missing_operator_facts: tuple[str, ...]
    conflicts: tuple[str, ...]
    provisional_decision: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence": [item.to_dict() for item in self.evidence],
            "missing_operator_facts": list(self.missing_operator_facts),
            "conflicts": list(self.conflicts),
            "provisional_decision": self.provisional_decision,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class EvidenceLedgerParse:
    parse_status: str
    raw_output: str
    parsed: EvidenceLedger | None = None
    error_code: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "parse_status": self.parse_status,
            "raw_output": self.raw_output,
            "parsed": self.parsed.to_dict() if self.parsed else None,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


@dataclass(frozen=True)
class PreplanIssue:
    code: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class PreplanReport:
    valid: bool
    containment_stage: str
    issues: tuple[PreplanIssue, ...]
    verified_evidence_paths: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "containment_stage": self.containment_stage,
            "issues": [issue.to_dict() for issue in self.issues],
            "verified_evidence_paths": list(self.verified_evidence_paths),
        }


class LedgerContractError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def parse_evidence_ledger(raw_output: str) -> EvidenceLedgerParse:
    """Parse one strict M3 ledger and preserve every malformed result."""

    if not isinstance(raw_output, str):
        raise TypeError("raw_output must be text")
    try:
        payload = json.loads(
            raw_output,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_number,
        )
        parsed = _validate_payload(payload)
    except json.JSONDecodeError as error:
        return _parse_error(
            raw_output,
            "invalid_json",
            f"{error.msg} at line {error.lineno} column {error.colno}",
        )
    except LedgerContractError as error:
        return _parse_error(raw_output, error.code, str(error))
    return EvidenceLedgerParse(
        parse_status="PARSED",
        raw_output=raw_output,
        parsed=parsed,
    )


def validate_evidence_ledger(
    parsed: EvidenceLedgerParse,
    context: Mapping[str, Any],
) -> PreplanReport:
    """Validate ledger provenance and internal decision consistency."""

    validate_agent_visible_context(context)
    if parsed.parsed is None:
        return PreplanReport(
            valid=False,
            containment_stage="pre_plan_ledger_parse",
            issues=(
                PreplanIssue(
                    code=parsed.error_code or "ledger_parse_error",
                    path="first_call",
                    message=parsed.error_message or "ledger did not parse",
                ),
            ),
            verified_evidence_paths=(),
        )

    issues: list[PreplanIssue] = []
    verified: list[str] = []
    for index, item in enumerate(parsed.parsed.evidence):
        path = f"evidence[{index}].source_path"
        if _contains_privileged_segment(item.source_path):
            issues.append(
                PreplanIssue(
                    code="privileged_evidence_path",
                    path=path,
                    message="evidence path names a privileged source field",
                )
            )
        elif not _path_exists(context, item.source_path):
            issues.append(
                PreplanIssue(
                    code="unknown_evidence_path",
                    path=path,
                    message="evidence path does not exist in AGENT context",
                )
            )
        else:
            verified.append(item.source_path)
    if issues:
        return PreplanReport(
            valid=False,
            containment_stage="pre_plan_evidence_provenance",
            issues=tuple(issues),
            verified_evidence_paths=tuple(verified),
        )

    ledger = parsed.parsed
    if ledger.provisional_decision == "EXECUTE" and (
        ledger.missing_operator_facts or ledger.conflicts
    ):
        issues.append(
            PreplanIssue(
                code="execute_with_reported_gap",
                path="provisional_decision",
                message="EXECUTE conflicts with a reported missing fact or conflict",
            )
        )
    elif (
        ledger.provisional_decision == "CLARIFY"
        and not ledger.missing_operator_facts
    ):
        issues.append(
            PreplanIssue(
                code="clarify_without_missing_fact",
                path="provisional_decision",
                message="CLARIFY requires a reported missing operator fact",
            )
        )
    elif ledger.provisional_decision == "BLOCK" and not ledger.conflicts:
        issues.append(
            PreplanIssue(
                code="block_without_conflict",
                path="provisional_decision",
                message="BLOCK requires a reported conflict",
            )
        )
    if issues:
        return PreplanReport(
            valid=False,
            containment_stage="pre_plan_decision_consistency",
            issues=tuple(issues),
            verified_evidence_paths=tuple(verified),
        )
    return PreplanReport(
        valid=True,
        containment_stage="pre_plan_accepted",
        issues=(),
        verified_evidence_paths=tuple(verified),
    )


def _validate_payload(payload: Any) -> EvidenceLedger:
    if not isinstance(payload, Mapping) or set(payload) != LEDGER_FIELDS:
        raise LedgerContractError(
            "ledger_schema_mismatch",
            f"ledger fields must be exactly {sorted(LEDGER_FIELDS)}",
        )
    evidence = payload["evidence"]
    if not isinstance(evidence, list):
        raise LedgerContractError("evidence_not_array", "evidence must be an array")
    items: list[EvidenceItem] = []
    for index, value in enumerate(evidence):
        if not isinstance(value, Mapping) or set(value) != EVIDENCE_FIELDS:
            raise LedgerContractError(
                "evidence_item_schema_mismatch",
                f"evidence[{index}] fields must be exactly {sorted(EVIDENCE_FIELDS)}",
            )
        items.append(
            EvidenceItem(
                source_path=_text(
                    value["source_path"],
                    f"evidence[{index}].source_path",
                ),
                claim=_text(value["claim"], f"evidence[{index}].claim"),
            )
        )
    missing = _text_array(
        payload["missing_operator_facts"],
        "missing_operator_facts",
    )
    conflicts = _text_array(payload["conflicts"], "conflicts")
    decision = payload["provisional_decision"]
    if not isinstance(decision, str) or decision not in PROVISIONAL_DECISIONS:
        raise LedgerContractError(
            "invalid_provisional_decision",
            "provisional_decision must be EXECUTE, CLARIFY, or BLOCK",
        )
    return EvidenceLedger(
        evidence=tuple(items),
        missing_operator_facts=missing,
        conflicts=conflicts,
        provisional_decision=str(decision),
        reason=_text(payload["reason"], "reason"),
    )


def _path_exists(context: Mapping[str, Any], path: str) -> bool:
    if path == "instruction":
        return True
    if not re.fullmatch(
        r"(?:session|environment|observation_contract)(?:\.[A-Za-z0-9_]+)+"
        r"|drones\[\d+\](?:\.[A-Za-z0-9_]+)+",
        path,
    ):
        return False
    current: Any = context
    for key, index in re.findall(r"([A-Za-z0-9_]+)(?:\[(\d+)\])?", path):
        if not isinstance(current, Mapping) or key not in current:
            return False
        current = current[key]
        if index:
            if not isinstance(current, list) or int(index) >= len(current):
                return False
            current = current[int(index)]
    return True


def _contains_privileged_segment(path: str) -> bool:
    segments = set(re.findall(r"[A-Za-z0-9_]+", path))
    return bool(segments & PRIVILEGED_SOURCE_FIELDS)


def _text_array(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise LedgerContractError(f"{label}_not_array", f"{label} must be an array")
    return tuple(_text(item, f"{label}[{index}]") for index, item in enumerate(value))


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LedgerContractError(
            "empty_required_text",
            f"{label} must be non-empty text",
        )
    return value.strip()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LedgerContractError("duplicate_json_key", f"duplicate key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_number(value: str) -> None:
    raise LedgerContractError("nonfinite_number", f"non-finite number: {value}")


def _parse_error(
    raw_output: str,
    code: str,
    message: str,
) -> EvidenceLedgerParse:
    return EvidenceLedgerParse(
        parse_status="PARSE_ERROR",
        raw_output=raw_output,
        error_code=code,
        error_message=message,
    )
