import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

try:
    from backend.mission_dataset import validate_dataset
except ImportError:
    from mission_dataset import validate_dataset


REVIEW_SCHEMA = "shepherd-reviewed-shadow-augmentation/1.0"
APPROVED_ACTIVE = "approved_active"
APPROVED_SHADOW = "approved_shadow"
MANUAL_CORRECTED = "manual_corrected"
APPROVED_STATUSES = {APPROVED_ACTIVE, APPROVED_SHADOW, MANUAL_CORRECTED}
INTENT_FIELDS = {"action", "target_zone", "target_reference", "drone_count", "pattern", "priority"}
REQUIRED_INTENT_FIELDS = {"action", "target_zone", "drone_count", "pattern"}
DEFAULT_CONSTRAINTS = {
    "confirmation_required": True,
    "nav_mode": "gnss",
    "live_dispatch_requested": False,
}


def load_review_candidates(path: str | Path) -> List[Dict]:
    candidates = []
    input_path = Path(path)
    with input_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                candidate = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{input_path}:{line_number}: invalid JSON: {exc}") from exc
            candidate["_line_number"] = line_number
            candidates.append(candidate)
    return candidates


def build_reviewed_rows(candidates: List[Dict], id_prefix: str = "reviewed_shadow") -> Dict:
    rows = []
    errors = []
    skipped = []
    seen_ids = set()

    for candidate in candidates:
        status = candidate.get("expected_intent_status")
        if status not in APPROVED_STATUSES:
            skipped.append({
                "candidate_id": candidate.get("candidate_id"),
                "reason": f"not approved for training: {status or 'missing_status'}",
            })
            continue

        try:
            row = _candidate_to_dataset_row(candidate, status, id_prefix)
        except ValueError as exc:
            errors.append({
                "candidate_id": candidate.get("candidate_id"),
                "line": candidate.get("_line_number"),
                "error": str(exc),
            })
            continue

        if row["id"] in seen_ids:
            errors.append({
                "candidate_id": candidate.get("candidate_id"),
                "line": candidate.get("_line_number"),
                "error": f"duplicate generated id {row['id']}",
            })
            continue
        seen_ids.add(row["id"])
        rows.append(row)

    return {
        "schema": REVIEW_SCHEMA,
        "ready_for_training": not errors,
        "review_required": False,
        "summary": {
            "input_count": len(candidates),
            "approved_count": len(rows),
            "skipped_count": len(skipped),
            "error_count": len(errors),
        },
        "rows": rows,
        "skipped": skipped,
        "errors": errors,
    }


def write_reviewed_rows(rows: List[Dict], output_path: str | Path) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    return str(path)


def promote_reviewed_candidates(
    input_path: str | Path,
    output_path: str | Path,
    *,
    id_prefix: str = "reviewed_shadow",
    allow_empty: bool = False,
) -> Dict:
    candidates = load_review_candidates(input_path)
    result = build_reviewed_rows(candidates, id_prefix=id_prefix)
    if result["errors"]:
        result["output_path"] = None
        result["valid"] = False
        return result
    if not result["rows"] and not allow_empty:
        result["errors"].append({"error": "no approved candidates to write"})
        result["ready_for_training"] = False
        result["output_path"] = None
        result["valid"] = False
        return result

    result["output_path"] = write_reviewed_rows(result["rows"], output_path)
    validation = validate_dataset(output_path)
    result["validation"] = validation
    result["valid"] = bool(validation["valid"])
    result["ready_for_training"] = bool(validation["valid"])
    return result


def _candidate_to_dataset_row(candidate: Dict, status: str, id_prefix: str) -> Dict:
    command = candidate.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ValueError("candidate command must be a non-empty string")

    expected_intent = _select_expected_intent(candidate, status)
    missing = sorted(REQUIRED_INTENT_FIELDS - set(expected_intent))
    if missing:
        raise ValueError(f"expected_intent missing required fields: {', '.join(missing)}")
    if not isinstance(expected_intent.get("drone_count"), int) or expected_intent["drone_count"] < 1:
        raise ValueError("expected_intent.drone_count must be a positive integer")

    constraints = dict(DEFAULT_CONSTRAINTS)
    if isinstance(candidate.get("expected_constraints"), dict):
        constraints.update(candidate["expected_constraints"])

    return {
        "id": _row_id(id_prefix, candidate.get("candidate_id")),
        "language": candidate.get("language") if candidate.get("language") in {"en", "ar"} else _detect_language(command),
        "split": "train",
        "command": command.strip(),
        "expected_intent": expected_intent,
        "expected_constraints": constraints,
        "should_clarify": _should_clarify(candidate, expected_intent),
        "notes": _notes(candidate, status),
    }


def _select_expected_intent(candidate: Dict, status: str) -> Dict:
    if status == MANUAL_CORRECTED:
        selected = candidate.get("expected_intent")
    else:
        options = candidate.get("expected_intent_options") or {}
        selected = options.get("active") if status == APPROVED_ACTIVE else options.get("shadow")
    if not isinstance(selected, dict):
        raise ValueError(f"{status} requires a JSON object expected intent")

    intent = {
        field: selected[field]
        for field in sorted(INTENT_FIELDS)
        if field in selected and selected[field] is not None
    }
    intent.setdefault("priority", "medium")
    return intent


def _row_id(id_prefix: str, candidate_id: str | None) -> str:
    raw = f"{id_prefix}_{candidate_id or 'unknown'}"
    return re.sub(r"[^a-zA-Z0-9_]+", "_", raw).strip("_").lower()


def _detect_language(command: str) -> str:
    return "ar" if re.search(r"[\u0600-\u06ff]", command) else "en"


def _should_clarify(candidate: Dict, expected_intent: Dict) -> bool:
    if isinstance(candidate.get("should_clarify"), bool):
        return candidate["should_clarify"]
    target = str(expected_intent.get("target_zone", "")).strip().lower()
    return target in {"unknown", "", "undefined"}


def _notes(candidate: Dict, status: str) -> str:
    mismatch_fields = ", ".join(candidate.get("mismatch_fields", []) or [])
    evidence_id = candidate.get("evidence_id", "unknown")
    base = f"Reviewed parser-shadow candidate from {evidence_id}; status={status}."
    if mismatch_fields:
        base += f" Mismatch fields: {mismatch_fields}."
    existing = candidate.get("notes")
    if existing:
        base += f" Source notes: {existing}"
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote manually reviewed parser shadow candidates into dataset rows.")
    parser.add_argument("--input", required=True, help="Reviewed parser shadow candidate JSONL path.")
    parser.add_argument("--output", required=True, help="Output JSONL path for dataset-compatible train rows.")
    parser.add_argument("--id-prefix", default="reviewed_shadow", help="Prefix for generated dataset row ids.")
    parser.add_argument("--allow-empty", action="store_true", help="Write an empty output file when no candidates are approved.")
    args = parser.parse_args()

    result = promote_reviewed_candidates(
        args.input,
        args.output,
        id_prefix=args.id_prefix,
        allow_empty=args.allow_empty,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
