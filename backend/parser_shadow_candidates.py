import argparse
import json
import time
from pathlib import Path
from typing import Dict, List

try:
    from backend.evidence_log import EvidenceLogger
    from backend.parser_shadow_report import generate_parser_shadow_report
    from backend.signing import SignatureManager
except ImportError:
    from evidence_log import EvidenceLogger
    from parser_shadow_report import generate_parser_shadow_report
    from signing import SignatureManager


DEFAULT_LIMIT = 100
DEFAULT_OUTPUT_PATH = Path(".tmp_scenarios/parser-shadow-candidates.jsonl")
CANDIDATE_SCHEMA = "shepherd-parser-shadow-candidates/1.0"


def generate_parser_shadow_candidates(
    evidence_dir: str | Path | None = None,
    limit: int = DEFAULT_LIMIT,
    signer: SignatureManager | None = None,
    include_matches: bool = False,
    evidence_logger: EvidenceLogger | None = None,
) -> Dict:
    """Extract reviewable dataset-improvement candidates from parser shadow evidence."""
    logger = evidence_logger or EvidenceLogger(evidence_dir, signer=signer)
    shadow_report = generate_parser_shadow_report(
        limit=limit,
        include_records=True,
        evidence_logger=logger,
    )
    candidates = []
    for record in shadow_report.get("records", []):
        candidates.extend(_record_candidates(record, include_matches=include_matches))

    return {
        "schema": CANDIDATE_SCHEMA,
        "generated_at": time.time(),
        "evidence_dir": shadow_report.get("evidence_dir"),
        "limit": limit,
        "include_matches": include_matches,
        "ready_for_training": False,
        "review_required": True,
        "summary": _summary(candidates, shadow_report),
        "candidates": candidates,
        "usage": {
            "review_note": "These rows preserve active and shadow parser outputs for human review. Do not append them to training data until expected_intent is manually selected or corrected.",
            "training_guard": "Generated candidates are not dataset-compatible training rows by default.",
        },
    }


def write_candidates_jsonl(result: Dict, output_path: str | Path = DEFAULT_OUTPUT_PATH) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for candidate in result.get("candidates", []):
            handle.write(json.dumps(candidate, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    return str(path)


def _record_candidates(record: Dict, include_matches: bool) -> List[Dict]:
    candidates = []
    command = record.get("command")
    for index, audit in enumerate(record.get("parser_shadow_audits", []) or [], 1):
        if audit.get("status") == "failed":
            candidates.append(_failed_candidate(record, audit, index))
            continue
        if audit.get("matches_active") and not include_matches:
            continue
        candidates.append(_comparison_candidate(record, audit, index, command))
    return candidates


def _comparison_candidate(record: Dict, audit: Dict, index: int, command: str | None) -> Dict:
    mismatches = audit.get("mismatches", []) or []
    mismatch_fields = [item.get("field", "unknown") for item in mismatches]
    candidate_id = _candidate_id(record.get("evidence_id"), index)
    return {
        "candidate_id": candidate_id,
        "source": "parser_shadow_audit",
        "evidence_id": record.get("evidence_id"),
        "plan_id": record.get("plan_id"),
        "command": command,
        "active_parser": audit.get("active_parser"),
        "shadow_parser": audit.get("shadow_parser"),
        "model_id": audit.get("model_id"),
        "model_digest": audit.get("model_digest"),
        "matches_active": bool(audit.get("matches_active")),
        "mismatch_fields": mismatch_fields,
        "mismatches": mismatches,
        "active_intent": audit.get("active_intent", {}),
        "shadow_intent": audit.get("shadow_intent", {}),
        "expected_intent_status": "unreviewed",
        "expected_intent_options": {
            "active": audit.get("active_intent", {}),
            "shadow": audit.get("shadow_intent", {}),
            "manual": None,
        },
        "suggested_review_fields": mismatch_fields,
        "ready_for_training": False,
        "notes": "Review required: choose or correct expected_intent before promoting into targeted augmentation.",
    }


def _failed_candidate(record: Dict, audit: Dict, index: int) -> Dict:
    return {
        "candidate_id": _candidate_id(record.get("evidence_id"), index),
        "source": "parser_shadow_audit",
        "evidence_id": record.get("evidence_id"),
        "plan_id": record.get("plan_id"),
        "command": record.get("command"),
        "active_parser": audit.get("active_parser"),
        "shadow_parser": audit.get("shadow_parser"),
        "status": "shadow_failed",
        "error": audit.get("error"),
        "expected_intent_status": "unreviewed",
        "expected_intent_options": {},
        "ready_for_training": False,
        "notes": "Shadow parser failed; inspect artifact/runtime before using this as training evidence.",
    }


def _candidate_id(evidence_id: str | None, index: int) -> str:
    safe_evidence = (evidence_id or "unknown").replace("evidence-", "")
    return f"shadow_{safe_evidence}_{index:03d}"


def _summary(candidates: List[Dict], shadow_report: Dict) -> Dict:
    mismatch_field_counts = {}
    parser_pairs = {}
    failed_count = 0
    for candidate in candidates:
        if candidate.get("status") == "shadow_failed":
            failed_count += 1
        pair = f"{candidate.get('active_parser', 'unknown')}->{candidate.get('shadow_parser', 'unknown')}"
        parser_pairs[pair] = parser_pairs.get(pair, 0) + 1
        for field in candidate.get("mismatch_fields", []) or []:
            mismatch_field_counts[field] = mismatch_field_counts.get(field, 0) + 1
    return {
        "candidate_count": len(candidates),
        "failed_shadow_count": failed_count,
        "mismatch_field_counts": mismatch_field_counts,
        "parser_pairs": parser_pairs,
        "shadow_report_summary": shadow_report.get("summary", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export reviewable parser shadow disagreement candidates.")
    parser.add_argument("--evidence-dir", default=None, help="Evidence directory. Defaults to SHEPHERD_EVIDENCE_DIR or evidence/.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Maximum evidence records to scan.")
    parser.add_argument("--include-matches", action="store_true", help="Include matching active-vs-shadow comparisons.")
    parser.add_argument("--output", default=None, help="Optional JSONL output path for candidates.")
    parser.add_argument("--summary-only", action="store_true", help="Omit candidate details from stdout.")
    args = parser.parse_args()

    result = generate_parser_shadow_candidates(
        evidence_dir=args.evidence_dir,
        limit=args.limit,
        include_matches=args.include_matches,
    )
    if args.output:
        result["output_path"] = write_candidates_jsonl(result, args.output)
    rendered = dict(result)
    if args.summary_only:
        rendered["candidates"] = []
    print(json.dumps(rendered, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
