import argparse
import json
import time
from pathlib import Path
from typing import Dict, List

try:
    from backend.evidence_log import EvidenceLogger
    from backend.evidence_replay import EvidenceReplayHarness
    from backend.signing import SignatureManager
except ImportError:
    from evidence_log import EvidenceLogger
    from evidence_replay import EvidenceReplayHarness
    from signing import SignatureManager


DEFAULT_LIMIT = 100
ASSURANCE_MONITORS = [
    "battery_reserve",
    "altitude_envelope",
    "safety_replay_status",
    "localization_confidence",
    "link_health",
    "selected_vehicle_consistency",
]


def generate_assurance_report(
    evidence_dir: str | Path | None = None,
    limit: int = DEFAULT_LIMIT,
    signer: SignatureManager | None = None,
    include_records: bool = True,
    evidence_logger: EvidenceLogger | None = None,
) -> Dict:
    """Summarize report-only runtime assurance evidence across confirmed missions."""
    logger = evidence_logger or EvidenceLogger(evidence_dir, signer=signer)
    logger._ensure_root()
    harness = EvidenceReplayHarness(logger)
    paths = _record_paths(logger, limit)

    records = []
    summary = _empty_summary()
    monitor_counts = {}
    fallback_counts = {}
    selected_vehicles = set()

    for path in paths:
        record_report = _record_report(logger, harness, path)
        records.append(record_report)
        _merge_record(summary, monitor_counts, fallback_counts, selected_vehicles, record_report)

    summary["monitor_counts"] = monitor_counts
    summary["fallback_recommendations"] = fallback_counts
    summary["selected_vehicle_count"] = len(selected_vehicles)

    return {
        "report": "runtime_assurance_evidence",
        "generated_at": time.time(),
        "evidence_dir": str(logger.root_dir),
        "limit": limit,
        "report_only": True,
        "summary": summary,
        "validation_scope": {
            "monitors": ASSURANCE_MONITORS,
            "automatic_fallback_enabled": False,
            "dispatch_side_effects": False,
            "dispatch_note": "This report reads signed evidence only; it does not call MAVSDK or command vehicles.",
        },
        "records": records if include_records else [],
    }


def write_assurance_report(result: Dict, report_path: str | Path) -> str:
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


def _record_report(logger: EvidenceLogger, harness: EvidenceReplayHarness, path: Path) -> Dict:
    evidence_id = path.stem
    try:
        record = logger.read_record(evidence_id)
        replay = harness.replay_record(record)
    except Exception as exc:
        return {
            "evidence_id": evidence_id,
            "path": str(path),
            "readable": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "evidence_verified": False,
            "replay_verified": False,
            "assurance_summary": {},
            "assurance_events": [],
            "critical_events": [],
        }

    verification = record.get("verification", {})
    replay_summary = replay.get("summary", {})
    assurance_events = record.get("assurance_events", []) or []
    critical_events = [event for event in assurance_events if event.get("severity") == "critical"]
    mission_programs = record.get("mission_programs", []) or []
    live_dispatch_requested = any(
        bool((program.get("constraints") or {}).get("live_dispatch_requested"))
        for program in mission_programs
    )

    return {
        "evidence_id": evidence_id,
        "path": str(path),
        "readable": True,
        "recorded_at": record.get("recorded_at"),
        "plan_id": record.get("plan_id"),
        "command": record.get("command"),
        "selected_drones": record.get("selected_drones", []),
        "mission_program_count": len(mission_programs),
        "live_dispatch_requested": live_dispatch_requested,
        "evidence_verified": bool(verification.get("digest_valid") and verification.get("signature_valid")),
        "replay_verified": bool(replay_summary.get("verified")),
        "replay_summary": replay_summary,
        "assurance_summary": record.get("assurance_summary", {}) or {},
        "assurance_events": assurance_events,
        "critical_events": critical_events,
    }


def _empty_summary() -> Dict:
    return {
        "total_records": 0,
        "readable_records": 0,
        "evidence_verified": 0,
        "evidence_failed": 0,
        "replay_verified": 0,
        "replay_failed": 0,
        "mission_program_count": 0,
        "live_dispatch_requested": 0,
        "assurance_event_count": 0,
        "critical_count": 0,
        "warning_count": 0,
        "info_count": 0,
        "records_with_critical_events": 0,
    }


def _merge_record(
    summary: Dict,
    monitor_counts: Dict,
    fallback_counts: Dict,
    selected_vehicles: set,
    record_report: Dict,
) -> None:
    summary["total_records"] += 1
    if not record_report.get("readable"):
        summary["evidence_failed"] += 1
        summary["replay_failed"] += 1
        return

    summary["readable_records"] += 1
    summary["mission_program_count"] += int(record_report.get("mission_program_count", 0))
    if record_report.get("live_dispatch_requested"):
        summary["live_dispatch_requested"] += 1
    if record_report.get("evidence_verified"):
        summary["evidence_verified"] += 1
    else:
        summary["evidence_failed"] += 1
    if record_report.get("replay_verified"):
        summary["replay_verified"] += 1
    else:
        summary["replay_failed"] += 1

    for drone_id in record_report.get("selected_drones", []):
        selected_vehicles.add(drone_id)

    critical_seen = False
    for event in record_report.get("assurance_events", []):
        severity = event.get("severity", "info")
        monitor = event.get("monitor", "unknown")
        fallback = event.get("fallback_recommendation", "none")
        summary["assurance_event_count"] += 1
        summary[f"{severity}_count"] = summary.get(f"{severity}_count", 0) + 1
        monitor_counts[monitor] = monitor_counts.get(monitor, 0) + 1
        fallback_counts[fallback] = fallback_counts.get(fallback, 0) + 1
        if severity == "critical":
            critical_seen = True

    if critical_seen:
        summary["records_with_critical_events"] += 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a report-only Shepherd-AI runtime assurance report.")
    parser.add_argument("--evidence-dir", default=None, help="Evidence directory. Defaults to SHEPHERD_EVIDENCE_DIR or evidence/.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Maximum evidence records to summarize.")
    parser.add_argument("--report", default=None, help="Optional path to write the full JSON assurance report.")
    parser.add_argument("--summary-only", action="store_true", help="Omit per-record evidence details from stdout/report.")
    args = parser.parse_args()

    result = generate_assurance_report(
        evidence_dir=args.evidence_dir,
        limit=args.limit,
        include_records=not args.summary_only,
    )
    if args.report:
        result["report_path"] = write_assurance_report(result, args.report)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
