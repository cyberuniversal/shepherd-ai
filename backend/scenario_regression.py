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

    def run(
        self,
        limit: int = DEFAULT_LIMIT,
        manifest_path: str | Path | None = None,
        include_cases: bool = True,
    ) -> Dict:
        self.evidence_logger._ensure_root()
        manifest = self._load_manifest(manifest_path) if manifest_path else None
        case_specs = self._manifest_case_specs(manifest, limit) if manifest else self._record_case_specs(limit)
        cases = [self._run_case(path, scenario) for path, scenario in case_specs]
        failed = [case for case in cases if not case["passed"]]
        expectation_failed = [case for case in cases if not case["expectation_met"]]
        status = "no_records" if not cases else ("passed" if not expectation_failed else "failed")
        summary = self._summary(cases, failed, expectation_failed)

        return {
            "suite": "scenario_regression",
            "status": status,
            "passed": status != "failed",
            "ran_at": time.time(),
            "evidence_dir": str(self.evidence_logger.root_dir),
            "limit": limit,
            "manifest": self._manifest_summary(manifest, manifest_path),
            "summary": summary,
            "cases": cases if include_cases else [],
        }

    def _record_case_specs(self, limit: int) -> List[tuple[Path, Dict | None]]:
        limit = max(1, min(int(limit), 1000))
        paths = sorted(
            self.evidence_logger.root_dir.glob("evidence-*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )[:limit]
        return [(path, None) for path in paths]

    def _manifest_case_specs(self, manifest: Dict, limit: int) -> List[tuple[Path, Dict | None]]:
        limit = max(1, min(int(limit), 1000))
        specs = []
        for scenario in manifest.get("scenarios", [])[:limit]:
            evidence_id = scenario.get("evidence_id")
            if not evidence_id:
                continue
            specs.append((self.evidence_logger._record_path(evidence_id), scenario))
        return specs

    def _run_case(self, path: Path, scenario: Dict | None = None) -> Dict:
        evidence_id = (scenario or {}).get("evidence_id") or path.stem
        try:
            replay = self.replay_harness.replay(evidence_id)
            reasons = self._failure_reasons(replay)
            assurance = self._assurance_from_record(evidence_id)
            case = {
                **self._scenario_fields(scenario),
                "evidence_id": evidence_id,
                "path": str(path),
                "passed": not reasons,
                "failure_reasons": reasons,
                "replay_status": replay.get("status"),
                "summary": replay.get("summary", {}),
                "checks": self._checks_from_replay(replay),
                "assurance": assurance,
            }
            return self._with_expectation(case, scenario)
        except Exception as exc:
            assurance = self._assurance_from_record(evidence_id)
            case = {
                **self._scenario_fields(scenario),
                "evidence_id": evidence_id,
                "path": str(path),
                "passed": False,
                "failure_reasons": [f"replay_error: {exc}"],
                "error_type": type(exc).__name__,
                "checks": {},
                "assurance": assurance,
            }
            return self._with_expectation(case, scenario)

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

    def _checks_from_replay(self, replay: Dict) -> Dict:
        summary = replay.get("summary", {})
        consistency = replay.get("record_consistency", {})
        return {
            "evidence_integrity_ok": bool(summary.get("evidence_integrity_ok")),
            "mission_digest_valid": bool(summary.get("mission_digests_ok")),
            "mission_signature_valid": bool(summary.get("mission_signatures_ok")),
            "record_consistency_ok": bool(summary.get("record_consistency_ok")),
            "selected_drones_match_programs": bool(consistency.get("selected_drones_match_programs")),
            "replayed_safety_passed": bool(summary.get("replayed_safety_passed")),
            "replayed_safety_matches_record": bool(summary.get("replayed_safety_matches_record")),
        }

    def _assurance_from_record(self, evidence_id: str) -> Dict:
        try:
            record = self.evidence_logger.read_record(evidence_id)
        except Exception as exc:
            return {
                "available": False,
                "error": str(exc),
                "critical_count": 0,
                "warning_count": 0,
                "critical_monitors": [],
                "monitors": [],
            }

        events = record.get("assurance_events", []) or []
        critical_events = [event for event in events if event.get("severity") == "critical"]
        summary = record.get("assurance_summary", {}) or {}
        critical_count = summary.get("critical_count")
        warning_count = summary.get("warning_count")
        if critical_count is None:
            critical_count = len(critical_events)
        if warning_count is None:
            warning_count = len([event for event in events if event.get("severity") == "warning"])
        return {
            "available": True,
            "summary": summary,
            "event_count": len(events),
            "critical_count": int(critical_count),
            "warning_count": int(warning_count),
            "critical_monitors": self._unique(event.get("monitor") for event in critical_events),
            "monitors": self._unique(event.get("monitor") for event in events),
        }

    def _scenario_fields(self, scenario: Dict | None) -> Dict:
        if not scenario:
            return {}
        return {
            "scenario_id": scenario.get("scenario_id"),
            "description": scenario.get("description"),
            "expected_pass": scenario.get("expected_pass", True),
            "expected_failure_reasons": scenario.get("expected_failure_reasons", []),
            "expected_assurance_critical_count": scenario.get("expected_assurance_critical_count", 0),
            "expected_assurance_monitors": scenario.get("expected_assurance_monitors", []),
        }

    def _with_expectation(self, case: Dict, scenario: Dict | None) -> Dict:
        failures = []
        if scenario:
            expected_pass = bool(scenario.get("expected_pass", True))
            if case["passed"] != expected_pass:
                failures.append(
                    f"expected {'pass' if expected_pass else 'failure'} but observed "
                    f"{'pass' if case['passed'] else 'failure'}"
                )

            expected_reasons = scenario.get("expected_failure_reasons", []) or []
            actual_reasons = case.get("failure_reasons", [])
            missing_reasons = [reason for reason in expected_reasons if reason not in actual_reasons]
            unexpected_reasons = [reason for reason in actual_reasons if reason not in expected_reasons]
            if missing_reasons:
                failures.append(f"missing expected failure reasons: {', '.join(missing_reasons)}")
            if unexpected_reasons:
                failures.append(f"unexpected failure reasons: {', '.join(unexpected_reasons)}")

            expected_critical = int(scenario.get("expected_assurance_critical_count", 0) or 0)
            actual_critical = int(case.get("assurance", {}).get("critical_count", 0))
            if actual_critical != expected_critical:
                failures.append(f"expected {expected_critical} critical assurance events but observed {actual_critical}")

            expected_monitors = scenario.get("expected_assurance_monitors", []) or []
            actual_monitors = case.get("assurance", {}).get("critical_monitors", [])
            missing_monitors = [monitor for monitor in expected_monitors if monitor not in actual_monitors]
            if missing_monitors:
                failures.append(f"missing expected assurance monitors: {', '.join(missing_monitors)}")
        else:
            failures.extend(case.get("failure_reasons", []))

        expectation_met = not failures
        if expectation_met and scenario and not case["passed"]:
            status = "expected_failure"
        elif expectation_met and case["passed"]:
            status = "passed"
        elif case.get("error_type"):
            status = "error"
        else:
            status = "expectation_mismatch"

        case["expectation_met"] = expectation_met
        case["expectation_failures"] = failures
        case["status"] = status
        return case

    def _summary(self, cases: List[Dict], failed: List[Dict], expectation_failed: List[Dict]) -> Dict:
        expected_failures = [case for case in cases if case.get("expected_pass") is False]
        unexpected_failures = [
            case
            for case in cases
            if not case["passed"] and case.get("expected_pass", True) is not False
        ]
        return {
            "total": len(cases),
            "passed": len(cases) - len(failed),
            "failed": len(failed),
            "expected_failures": len(expected_failures),
            "unexpected_failures": len(unexpected_failures),
            "expectation_met": len(cases) - len(expectation_failed),
            "expectation_failed": len(expectation_failed),
            "assurance_event_count": sum(case.get("assurance", {}).get("event_count", 0) for case in cases),
            "assurance_critical_count": sum(case.get("assurance", {}).get("critical_count", 0) for case in cases),
        }

    def _load_manifest(self, manifest_path: str | Path | None) -> Dict:
        path = Path(manifest_path)
        with path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        if not isinstance(manifest.get("scenarios"), list):
            raise ValueError("scenario manifest must contain a scenarios list")
        return manifest

    def _manifest_summary(self, manifest: Dict | None, manifest_path: str | Path | None) -> Dict | None:
        if not manifest:
            return None
        return {
            "path": str(manifest_path),
            "manifest_version": manifest.get("manifest_version"),
            "scenario_count": manifest.get("scenario_count", len(manifest.get("scenarios", []))),
            "generated_at": manifest.get("generated_at"),
        }

    def _unique(self, values) -> List[str]:
        return list(dict.fromkeys(value for value in values if value))


def write_regression_report(result: Dict, report_path: str | Path) -> str:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    return str(path)


def _manifest_evidence_dir(manifest_path: str | Path | None) -> str | None:
    if not manifest_path:
        return None
    path = Path(manifest_path)
    with path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    evidence_dir = manifest.get("evidence_dir")
    if evidence_dir:
        return evidence_dir
    return str(path.parent)


def run_scenario_regression(
    evidence_dir: str | Path | None = None,
    limit: int = DEFAULT_LIMIT,
    manifest_path: str | Path | None = None,
    include_cases: bool = True,
) -> Dict:
    if manifest_path and evidence_dir is None:
        evidence_dir = _manifest_evidence_dir(manifest_path)
    return ScenarioRegressionRunner(EvidenceLogger(evidence_dir)).run(
        limit=limit,
        manifest_path=manifest_path,
        include_cases=include_cases,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Shepherd-AI evidence records as scenario regressions.")
    parser.add_argument("--evidence-dir", default=None, help="Evidence directory. Defaults to SHEPHERD_EVIDENCE_DIR or evidence/.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Maximum evidence records to replay.")
    parser.add_argument("--manifest", default=None, help="Optional scenario manifest generated by backend.scenario_fixtures.")
    parser.add_argument("--report", default=None, help="Optional path to write the full JSON regression report.")
    parser.add_argument("--summary-only", action="store_true", help="Omit per-case details from stdout and API-style result.")
    args = parser.parse_args()

    result = run_scenario_regression(
        args.evidence_dir,
        limit=args.limit,
        manifest_path=args.manifest,
        include_cases=not args.summary_only,
    )
    if args.report:
        result["report_path"] = write_regression_report(result, args.report)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
