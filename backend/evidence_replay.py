import argparse
import json
import time
from typing import Dict, List, Tuple

try:
    from backend.evidence_log import EvidenceLogger
    from backend.safety import validate_mission_program
    from backend.signing import digest_payload
except ImportError:
    from evidence_log import EvidenceLogger
    from safety import validate_mission_program
    from signing import digest_payload


def _unique(values: List[str]) -> List[str]:
    return list(dict.fromkeys(value for value in values if value))


class EvidenceReplayHarness:
    """Replay confirmed-mission evidence through current deterministic checks."""

    def __init__(self, evidence_logger: EvidenceLogger):
        self.evidence_logger = evidence_logger

    def replay(self, evidence_id: str) -> Dict:
        return self.replay_record(self.evidence_logger.read_record(evidence_id))

    def replay_record(self, record: Dict) -> Dict:
        evidence_verification = self.evidence_logger.verify_record(record)
        current_positions = self._positions_from_record(record)
        mission_programs = record.get("mission_programs", [])
        safety_reports = record.get("safety_reports", [])

        mission_results = []
        for index, program in enumerate(mission_programs):
            recorded_digest = program.get("mission_digest")
            expected_digest = digest_payload(program, recursive_signature_fields=True)
            digest_valid = bool(recorded_digest) and recorded_digest == expected_digest
            signature = (program.get("provenance") or {}).get("signature") or {}
            signature_verification = self.evidence_logger.signer.verify_digest_signature(
                signature,
                recorded_digest,
                payload_type="shepherd_ir_bundle",
            )
            replayed_safety = validate_mission_program(program, current_positions)
            recorded_safety = safety_reports[index] if index < len(safety_reports) else None
            safety_match = self._safety_matches(recorded_safety, replayed_safety)

            mission_results.append({
                "index": index,
                "mission_id": program.get("mission_id"),
                "language": program.get("language"),
                "recorded_digest": recorded_digest,
                "expected_digest": expected_digest,
                "digest_valid": digest_valid,
                "signature": signature_verification,
                "safety_replay": replayed_safety,
                "recorded_safety_available": recorded_safety is not None,
                "safety_matches_recorded": safety_match,
            })

        consistency = self._record_consistency(record, mission_programs)
        summary = self._summary(evidence_verification, mission_results, consistency)
        return {
            "evidence_id": record.get("evidence_id"),
            "record_type": record.get("record_type"),
            "replayed_at": time.time(),
            "status": "verified" if summary["verified"] else "attention_required",
            "summary": summary,
            "evidence_verification": evidence_verification,
            "record_consistency": consistency,
            "mission_replays": mission_results,
        }

    def _positions_from_record(self, record: Dict) -> Dict[str, Tuple[float, float]]:
        snapshot = record.get("fleet_snapshot_at_confirmation") or {}
        positions = {}
        for drone in snapshot.get("drones", []):
            drone_id = drone.get("id")
            lat = drone.get("lat")
            lng = drone.get("lng")
            if drone_id and lat is not None and lng is not None:
                positions[drone_id] = (float(lat), float(lng))
        return positions

    def _record_consistency(self, record: Dict, mission_programs: List[Dict]) -> Dict:
        selected_from_programs = []
        program_digests = []
        for program in mission_programs:
            program_digests.append(program.get("mission_digest"))
            selected_from_programs.extend(program.get("allocation", {}).get("selected_vehicles", []))
            selected_from_programs.extend(
                drone_program.get("drone_id")
                for drone_program in program.get("drone_programs", [])
            )

        record_selected = _unique(record.get("selected_drones", []))
        program_selected = _unique(selected_from_programs)
        record_digests = [digest for digest in record.get("mission_digests", []) if digest]
        program_digests = [digest for digest in program_digests if digest]
        execution_results = record.get("execution_results", [])
        confirmed = bool((record.get("confirmation") or {}).get("confirmed"))

        selected_match = sorted(record_selected) == sorted(program_selected)
        digest_list_match = record_digests == program_digests
        execution_count_match = len(execution_results) == len(mission_programs)
        ok = bool(confirmed and selected_match and digest_list_match and execution_count_match)

        return {
            "ok": ok,
            "confirmed": confirmed,
            "selected_drones_match_programs": selected_match,
            "record_selected_drones": record_selected,
            "program_selected_drones": program_selected,
            "mission_digest_list_matches_programs": digest_list_match,
            "record_mission_digests": record_digests,
            "program_mission_digests": program_digests,
            "execution_count_matches_program_count": execution_count_match,
            "execution_result_count": len(execution_results),
            "mission_program_count": len(mission_programs),
        }

    def _safety_matches(self, recorded_safety: Dict | None, replayed_safety: Dict) -> bool:
        if recorded_safety is None:
            return False
        return (
            bool(recorded_safety.get("passed")) == bool(replayed_safety.get("passed"))
            and sorted(recorded_safety.get("issues", [])) == sorted(replayed_safety.get("issues", []))
        )

    def _summary(self, evidence_verification: Dict, mission_results: List[Dict], consistency: Dict) -> Dict:
        has_missions = bool(mission_results)
        evidence_ok = bool(evidence_verification.get("digest_valid") and evidence_verification.get("signature_valid"))
        mission_digests_ok = has_missions and all(item["digest_valid"] for item in mission_results)
        mission_signatures_ok = has_missions and all(
            item["signature"].get("digest_valid")
            and item["signature"].get("signature_valid")
            and item["signature"].get("payload_type_valid")
            for item in mission_results
        )
        safety_passed = has_missions and all(item["safety_replay"].get("passed") for item in mission_results)
        safety_matched = has_missions and all(item["safety_matches_recorded"] for item in mission_results)
        verified = bool(
            evidence_ok
            and mission_digests_ok
            and mission_signatures_ok
            and safety_passed
            and safety_matched
            and consistency.get("ok")
        )

        return {
            "verified": verified,
            "evidence_integrity_ok": evidence_ok,
            "mission_digests_ok": mission_digests_ok,
            "mission_signatures_ok": mission_signatures_ok,
            "replayed_safety_passed": safety_passed,
            "replayed_safety_matches_record": safety_matched,
            "record_consistency_ok": bool(consistency.get("ok")),
            "mission_count": len(mission_results),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay and verify a Shepherd-AI evidence record.")
    parser.add_argument("evidence_id", help="Evidence id, for example evidence-abc123")
    parser.add_argument("--evidence-dir", default=None, help="Evidence directory. Defaults to SHEPHERD_EVIDENCE_DIR or evidence/.")
    args = parser.parse_args()

    logger = EvidenceLogger(args.evidence_dir)
    result = EvidenceReplayHarness(logger).replay(args.evidence_id)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("summary", {}).get("verified") else 1


if __name__ == "__main__":
    raise SystemExit(main())
