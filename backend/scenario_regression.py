import argparse
import json
import time
from pathlib import Path
from typing import Dict, List

try:
    from backend.evidence_log import EvidenceLogger
    from backend.evidence_replay import EvidenceReplayHarness
except ImportError:
    from evidence_log import EvidenceLogger
    from evidence_replay import EvidenceReplayHarness


DEFAULT_LIMIT = 100


class ScenarioRegressionRunner:
    """Run signed evidence records as replayable regression scenarios."""

    def __init__(self, evidence_logger: EvidenceLogger):
        self.evidence_logger = evidence_logger
        self.replay_harness = EvidenceReplayHarness(evidence_logger)

    def run(self, limit: int = DEFAULT_LIMIT) -> Dict:
        self.evidence_logger._ensure_root()
        paths = self._record_paths(limit)
        cases = [self._run_case(path) for path in paths]
        failed = [case for case in cases if not case["passed"]]
        status = "no_records" if not cases else ("passed" if not failed else "failed")

        return {
            "suite": "scenario_regression",
            "status": status,
            "passed": status != "failed",
            "ran_at": time.time(),
            "evidence_dir": str(self.evidence_logger.root_dir),
            "limit": limit,
            "summary": {
                "total": len(cases),
                "passed": len(cases) - len(failed),
                "failed": len(failed),
            },
            "cases": cases,
        }

    def _record_paths(self, limit: int) -> List[Path]:
        limit = max(1, min(int(limit), 1000))
        return sorted(
            self.evidence_logger.root_dir.glob("evidence-*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )[:limit]

    def _run_case(self, path: Path) -> Dict:
        evidence_id = path.stem
        try:
            replay = self.replay_harness.replay(evidence_id)
            reasons = self._failure_reasons(replay)
            return {
                "evidence_id": evidence_id,
                "path": str(path),
                "passed": not reasons,
                "status": "passed" if not reasons else "failed",
                "failure_reasons": reasons,
                "replay_status": replay.get("status"),
                "summary": replay.get("summary", {}),
            }
        except Exception as exc:
            return {
                "evidence_id": evidence_id,
                "path": str(path),
                "passed": False,
                "status": "error",
                "failure_reasons": [f"replay_error: {exc}"],
                "error_type": type(exc).__name__,
            }

    def _failure_reasons(self, replay: Dict) -> List[str]:
        summary = replay.get("summary", {})
        consistency = replay.get("record_consistency", {})
        reasons = []
        if not summary.get("evidence_integrity_ok"):
            reasons.append("evidence_integrity_failed")
        if not summary.get("mission_digests_ok"):
            reasons.append("mission_digest_mismatch")
        if not summary.get("mission_signatures_ok"):
            reasons.append("mission_signature_failed")
        if not summary.get("record_consistency_ok"):
            reasons.append("record_consistency_failed")
        if not summary.get("replayed_safety_passed"):
            reasons.append("replayed_safety_failed")
        if not summary.get("replayed_safety_matches_record"):
            reasons.append("replayed_safety_changed")
        if consistency and not consistency.get("selected_drones_match_programs"):
            reasons.append("selected_drones_do_not_match_programs")
        return reasons


def run_scenario_regression(evidence_dir: str | Path | None = None, limit: int = DEFAULT_LIMIT) -> Dict:
    return ScenarioRegressionRunner(EvidenceLogger(evidence_dir)).run(limit=limit)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Shepherd-AI evidence records as scenario regressions.")
    parser.add_argument("--evidence-dir", default=None, help="Evidence directory. Defaults to SHEPHERD_EVIDENCE_DIR or evidence/.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Maximum evidence records to replay.")
    args = parser.parse_args()

    result = run_scenario_regression(args.evidence_dir, limit=args.limit)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
