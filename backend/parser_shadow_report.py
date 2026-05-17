import argparse
import json
import time
from pathlib import Path
from typing import Dict, List

try:
    from backend.evidence_log import EvidenceLogger
    from backend.signing import SignatureManager
except ImportError:
    from evidence_log import EvidenceLogger
    from signing import SignatureManager


DEFAULT_LIMIT = 100


def generate_parser_shadow_report(
    evidence_dir: str | Path | None = None,
    limit: int = DEFAULT_LIMIT,
    signer: SignatureManager | None = None,
    include_records: bool = True,
    evidence_logger: EvidenceLogger | None = None,
) -> Dict:
    """Summarize report-only active-vs-shadow parser comparisons from signed evidence."""
    logger = evidence_logger or EvidenceLogger(evidence_dir, signer=signer)
    logger._ensure_root()
    records = []
    summary = _empty_summary()
    active_parser_counts = {}
    shadow_parser_counts = {}
    mismatch_field_counts = {}

    for path in _record_paths(logger, limit):
        record_report = _record_report(logger, path)
        records.append(record_report)
        _merge_record(summary, active_parser_counts, shadow_parser_counts, mismatch_field_counts, record_report)

    summary["active_parser_counts"] = active_parser_counts
    summary["shadow_parser_counts"] = shadow_parser_counts
    summary["mismatch_field_counts"] = mismatch_field_counts

    return {
        "report": "parser_shadow_audit",
        "generated_at": time.time(),
        "evidence_dir": str(logger.root_dir),
        "limit": limit,
        "report_only": True,
        "summary": summary,
        "validation_scope": {
            "automatic_parser_switching": False,
            "dispatch_side_effects": False,
            "dispatch_note": "This report reads signed evidence only; it does not call MAVSDK or command vehicles.",
        },
        "records": records if include_records else [],
    }


def write_parser_shadow_report(result: Dict, report_path: str | Path) -> str:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    return str(path)


def _record_paths(logger: EvidenceLogger, limit: int) -> List[Path]:
    limit = max(1, min(int(limit), 1000))
    return sorted(
        logger.root_dir.glob("evidence-*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )[:limit]


def _record_report(logger: EvidenceLogger, path: Path) -> Dict:
    evidence_id = path.stem
    try:
        record = logger.read_record(evidence_id)
    except Exception as exc:
        return {
            "evidence_id": evidence_id,
            "path": str(path),
            "readable": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "evidence_verified": False,
            "parser_shadow_audits": [],
        }

    verification = record.get("verification", {})
    parser_summary = record.get("parser_summary", {}) or {}
    audits = parser_summary.get("parser_shadow_audits", []) or []
    return {
        "evidence_id": evidence_id,
        "path": str(path),
        "readable": True,
        "recorded_at": record.get("recorded_at"),
        "plan_id": record.get("plan_id"),
        "command": record.get("command"),
        "selected_drones": record.get("selected_drones", []),
        "evidence_verified": bool(verification.get("digest_valid") and verification.get("signature_valid")),
        "active_modes": parser_summary.get("modes", []),
        "parser_status_mode": parser_summary.get("mode"),
        "parser_shadow_audits": audits,
        "audit_count": len(audits),
    }


def _empty_summary() -> Dict:
    return {
        "total_records": 0,
        "readable_records": 0,
        "evidence_verified": 0,
        "evidence_failed": 0,
        "records_with_shadow_audits": 0,
        "audit_count": 0,
        "matched_count": 0,
        "mismatch_count": 0,
        "failed_audit_count": 0,
    }


def _merge_record(
    summary: Dict,
    active_parser_counts: Dict,
    shadow_parser_counts: Dict,
    mismatch_field_counts: Dict,
    record_report: Dict,
) -> None:
    summary["total_records"] += 1
    if not record_report.get("readable"):
        summary["evidence_failed"] += 1
        return

    summary["readable_records"] += 1
    if record_report.get("evidence_verified"):
        summary["evidence_verified"] += 1
    else:
        summary["evidence_failed"] += 1

    audits = record_report.get("parser_shadow_audits", []) or []
    if audits:
        summary["records_with_shadow_audits"] += 1
    for audit in audits:
        summary["audit_count"] += 1
        active_parser = audit.get("active_parser", "unknown")
        shadow_parser = audit.get("shadow_parser", "unknown")
        active_parser_counts[active_parser] = active_parser_counts.get(active_parser, 0) + 1
        shadow_parser_counts[shadow_parser] = shadow_parser_counts.get(shadow_parser, 0) + 1
        if audit.get("status") == "failed":
            summary["failed_audit_count"] += 1
            continue
        if audit.get("matches_active"):
            summary["matched_count"] += 1
        else:
            summary["mismatch_count"] += 1
        for mismatch in audit.get("mismatches", []) or []:
            field = mismatch.get("field", "unknown")
            mismatch_field_counts[field] = mismatch_field_counts.get(field, 0) + 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a report-only Shepherd-AI parser shadow audit report.")
    parser.add_argument("--evidence-dir", default=None, help="Evidence directory. Defaults to SHEPHERD_EVIDENCE_DIR or evidence/.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Maximum evidence records to summarize.")
    parser.add_argument("--report", default=None, help="Optional path to write the full JSON parser shadow report.")
    parser.add_argument("--summary-only", action="store_true", help="Omit per-record evidence details from stdout/report.")
    args = parser.parse_args()

    result = generate_parser_shadow_report(
        evidence_dir=args.evidence_dir,
        limit=args.limit,
        include_records=not args.summary_only,
    )
    if args.report:
        result["report_path"] = write_parser_shadow_report(result, args.report)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
