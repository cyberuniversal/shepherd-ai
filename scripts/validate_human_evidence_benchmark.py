"""Validate a fresh human-authored evidence-decision benchmark candidate."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


REQUIRED_FIELDS = (
    "id",
    "text",
    "decision_stage",
    "context_id",
    "expected_decision",
    "label_rationale",
    "split",
    "source",
    "data_type",
    "author_id",
    "reviewer_id",
    "label_status",
)
ALLOWED_DECISIONS = {"proceed", "clarify", "block"}
ALLOWED_STAGES = {
    "grounding_sufficiency",
    "preflight",
    "compound_grounding_and_preflight",
}
EXPECTED_SPLIT = "final_test"
EXPECTED_DATA_TYPE = "human_written_evidence_decision"
EXPECTED_LABEL_STATUS = "adjudicated"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--comparison",
        type=Path,
        action="append",
        default=[],
        help="Existing JSONL whose text/command fields must not overlap the candidate.",
    )
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--require-balanced", action="store_true")
    parser.add_argument("--minimum-per-decision", type=int, default=1)
    args = parser.parse_args()
    if args.minimum_per_decision <= 0:
        raise ValueError("--minimum-per-decision must be positive")

    rows = _read_jsonl(args.dataset)
    comparison_texts = _comparison_texts(args.comparison)
    errors: list[str] = []
    ids: set[str] = set()
    normalized_texts: set[str] = set()
    decision_counts: Counter[str] = Counter()
    context_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    for line_number, row in enumerate(rows, start=1):
        missing = [field for field in REQUIRED_FIELDS if field not in row]
        if missing:
            errors.append(
                f"line {line_number}: missing required fields: {', '.join(missing)}"
            )
            continue
        record_id = _text(row["id"])
        text = _text(row["text"])
        decision = _text(row["expected_decision"])
        stage = _text(row["decision_stage"])
        context_id = _text(row["context_id"])
        if not record_id or not text:
            errors.append(f"line {line_number}: id and text must be non-empty")
        if record_id in ids:
            errors.append(f"line {line_number}: duplicate id {record_id!r}")
        ids.add(record_id)
        normalized = _normalize(text)
        if normalized in normalized_texts:
            errors.append(f"line {line_number}: duplicate normalized command text")
        normalized_texts.add(normalized)
        if normalized in comparison_texts:
            errors.append(
                f"line {line_number}: command overlaps an existing comparison dataset"
            )
        if decision not in ALLOWED_DECISIONS:
            errors.append(f"line {line_number}: invalid expected_decision {decision!r}")
        else:
            decision_counts[decision] += 1
        if stage not in ALLOWED_STAGES:
            errors.append(f"line {line_number}: invalid decision_stage {stage!r}")
        if not context_id:
            errors.append(f"line {line_number}: context_id must be non-empty")
        else:
            context_counts[context_id] += 1
        if row["split"] != EXPECTED_SPLIT:
            errors.append(f"line {line_number}: split must be {EXPECTED_SPLIT!r}")
        if row["data_type"] != EXPECTED_DATA_TYPE:
            errors.append(
                f"line {line_number}: data_type must be {EXPECTED_DATA_TYPE!r}"
            )
        if row["label_status"] != EXPECTED_LABEL_STATUS:
            errors.append(
                f"line {line_number}: label_status must be {EXPECTED_LABEL_STATUS!r}"
            )
        if not _text(row["label_rationale"]):
            errors.append(f"line {line_number}: label_rationale must be non-empty")
        if _text(row["author_id"]) == _text(row["reviewer_id"]):
            errors.append(
                f"line {line_number}: author_id and reviewer_id must differ"
            )
        source_counts[_text(row["source"])] += 1

    for decision in sorted(ALLOWED_DECISIONS):
        if decision_counts[decision] < args.minimum_per_decision:
            errors.append(
                f"decision {decision!r} has {decision_counts[decision]} records; "
                f"minimum is {args.minimum_per_decision}"
            )
    if args.require_balanced and len(set(decision_counts.values())) != 1:
        errors.append(
            f"decision classes are not balanced: {dict(sorted(decision_counts.items()))}"
        )
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": str(args.dataset),
        "dataset_sha256": _sha256(args.dataset),
        "record_count": len(rows),
        "decision_counts": dict(sorted(decision_counts.items())),
        "context_counts": dict(sorted(context_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "comparison_files": [
            {"path": str(path), "sha256": _sha256(path)}
            for path in args.comparison
        ],
        "require_balanced": args.require_balanced,
        "minimum_per_decision": args.minimum_per_decision,
        "valid": not errors,
        "errors": errors,
        "claim_status": (
            "schema_and_overlap_validated_only"
            if not errors
            else "invalid_candidate_not_usable"
        ),
        "limitations": [
            "Validation does not prove that labels are semantically correct.",
            "Participant consent, sampling, and ethics requirements are outside this file check.",
            "A valid candidate is not an evaluated Shepherd-AI result.",
        ],
    }
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)


def _comparison_texts(paths: list[Path]) -> set[str]:
    texts: set[str] = set()
    for path in paths:
        for row in _read_jsonl(path):
            for field in ("text", "command"):
                value = row.get(field)
                if isinstance(value, str) and value.strip():
                    texts.add(_normalize(value))
    return texts


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"JSONL input must contain at least one object: {path}")
    return rows


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    main()
