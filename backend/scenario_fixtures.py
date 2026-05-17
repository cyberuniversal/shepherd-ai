import argparse
import json
import time
from pathlib import Path
from typing import Dict, List

try:
    from backend.assurance import evaluate_runtime_assurance
    from backend.controller import SwarmManager
    from backend.evidence_log import EvidenceLogger
    from backend.mission_program import compile_mission_program
    from backend.safety import validate_mission_program
    from backend.signing import SignatureManager
except ImportError:
    from assurance import evaluate_runtime_assurance
    from controller import SwarmManager
    from evidence_log import EvidenceLogger
    from mission_program import compile_mission_program
    from safety import validate_mission_program
    from signing import SignatureManager


DEFAULT_OUTPUT_DIR = ".tmp_scenarios"
MANIFEST_NAME = "scenario-manifest.json"
KAFD_TARGET = {"lat": 24.7610, "lng": 46.6402}
AL_NADA_TARGET = {"lat": 24.8012, "lng": 46.6808}
OUT_OF_BOUNDS_TARGET = {"lat": 25.45, "lng": 47.45}


def generate_scenario_records(output_dir: str | Path = DEFAULT_OUTPUT_DIR, signer: SignatureManager | None = None) -> Dict:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    logger = EvidenceLogger(output_path, signer=signer)
    scenarios = [
        _nominal_kafd(logger),
        _low_battery(logger),
        _disconnected_live_link(logger),
        _bad_altitude(logger),
        _selected_drone_mismatch(logger),
        _tampered_evidence(logger),
        _safety_rejected_route(logger),
        _operator_relative_target(logger),
    ]
    manifest = {
        "manifest_version": "1.0",
        "generated_at": time.time(),
        "evidence_dir": str(output_path),
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
    }
    manifest_path = output_path / MANIFEST_NAME
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return {
        "output_dir": str(output_path),
        "manifest_path": str(manifest_path),
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
    }


def _nominal_kafd(logger: EvidenceLogger) -> Dict:
    return _record_scenario(
        logger,
        scenario_id="nominal_kafd_scout",
        description="Nominal single-drone KAFD perimeter scout.",
        command="Send one drone to KAFD for a perimeter scan.",
        intent={"action": "scout", "target_zone": "kafd", "pattern": "perimeter", "drone_count": 1, "confidence": 0.92, "parser": "fixture"},
        target=KAFD_TARGET,
        drone_id="alpha-1",
        expected_pass=True,
    )


def _low_battery(logger: EvidenceLogger) -> Dict:
    return _record_scenario(
        logger,
        scenario_id="low_battery_selected_vehicle",
        description="Selected vehicle is below reserve; regression replay is intact but assurance reports critical battery.",
        command="Send alpha-1 to KAFD with low battery.",
        intent={"action": "scout", "target_zone": "kafd", "pattern": "perimeter", "drone_count": 1, "confidence": 0.9, "parser": "fixture"},
        target=KAFD_TARGET,
        drone_id="alpha-1",
        battery=10.0,
        expected_pass=True,
        expected_assurance_critical_count=1,
        expected_assurance_monitors=["battery_reserve"],
    )


def _disconnected_live_link(logger: EvidenceLogger) -> Dict:
    return _record_scenario(
        logger,
        scenario_id="disconnected_live_link",
        description="Live dispatch requested but selected vehicle has no MAVLink connection; assurance reports link health.",
        command="Send alpha-1 to KAFD in live mode.",
        intent={"action": "scout", "target_zone": "kafd", "pattern": "perimeter", "drone_count": 1, "confidence": 0.9, "parser": "fixture"},
        target=KAFD_TARGET,
        drone_id="alpha-1",
        live_mode=True,
        live_connected=False,
        expected_pass=True,
        expected_assurance_critical_count=1,
        expected_assurance_monitors=["link_health"],
    )


def _bad_altitude(logger: EvidenceLogger) -> Dict:
    return _record_scenario(
        logger,
        scenario_id="bad_altitude_envelope",
        description="Signed mission uses altitude outside the deterministic safety envelope.",
        command="Send alpha-1 too high over KAFD.",
        intent={"action": "scout", "target_zone": "kafd", "pattern": "perimeter", "drone_count": 1, "confidence": 0.86, "parser": "fixture"},
        target=KAFD_TARGET,
        drone_id="alpha-1",
        altitude_m=130.0,
        expected_pass=False,
        expected_failure_reasons=["replayed_safety_failed"],
        expected_assurance_critical_count=3,
        expected_assurance_monitors=["safety_replay_status", "altitude_envelope"],
    )


def _selected_drone_mismatch(logger: EvidenceLogger) -> Dict:
    return _record_scenario(
        logger,
        scenario_id="selected_drone_mismatch",
        description="Evidence selected_drones list does not match the signed SHEPHERD-IR allocation.",
        command="Send alpha-1 to KAFD but record beta-1 as selected.",
        intent={"action": "scout", "target_zone": "kafd", "pattern": "perimeter", "drone_count": 1, "confidence": 0.88, "parser": "fixture"},
        target=KAFD_TARGET,
        drone_id="alpha-1",
        assigned_override=["beta-1"],
        expected_pass=False,
        expected_failure_reasons=["record_consistency_failed", "selected_drones_do_not_match_programs"],
        expected_assurance_critical_count=1,
        expected_assurance_monitors=["selected_vehicle_consistency"],
    )


def _tampered_evidence(logger: EvidenceLogger) -> Dict:
    metadata = _record_scenario(
        logger,
        scenario_id="tampered_evidence_record",
        description="Evidence record is modified after signing.",
        command="Send one drone to Al Nada.",
        intent={"action": "scout", "target_zone": "al nada", "pattern": "perimeter", "drone_count": 1, "confidence": 0.89, "parser": "fixture"},
        target=AL_NADA_TARGET,
        drone_id="alpha-1",
        expected_pass=False,
        expected_failure_reasons=["evidence_integrity_failed"],
    )
    path = Path(metadata["path"])
    record = json.loads(path.read_text(encoding="utf-8"))
    record["command"] = "Tampered after signature"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    metadata["tampered"] = True
    return metadata


def _safety_rejected_route(logger: EvidenceLogger) -> Dict:
    return _record_scenario(
        logger,
        scenario_id="safety_rejected_route",
        description="Signed route target is outside the Riyadh operating bounds.",
        command="Send alpha-1 outside the operating area.",
        intent={"action": "scout", "target_zone": "outside operating area", "pattern": "perimeter", "drone_count": 1, "confidence": 0.8, "parser": "fixture"},
        target=OUT_OF_BOUNDS_TARGET,
        drone_id="alpha-1",
        expected_pass=False,
        expected_failure_reasons=["replayed_safety_failed"],
        expected_assurance_critical_count=1,
        expected_assurance_monitors=["safety_replay_status"],
    )


def _operator_relative_target(logger: EvidenceLogger) -> Dict:
    return _record_scenario(
        logger,
        scenario_id="operator_relative_target",
        description="Operator-relative target with resolved coordinates for replay.",
        command="Bring one drone to me.",
        intent={
            "action": "rendezvous",
            "target_zone": "operator_current_position",
            "target_reference": "operator",
            "pattern": "perimeter",
            "drone_count": 1,
            "confidence": 0.9,
            "parser": "fixture",
        },
        target={"lat": 24.7136, "lng": 46.6753},
        drone_id="alpha-1",
        expected_pass=True,
    )


def _record_scenario(
    logger: EvidenceLogger,
    scenario_id: str,
    description: str,
    command: str,
    intent: Dict,
    target: Dict,
    drone_id: str,
    expected_pass: bool,
    expected_failure_reasons: List[str] | None = None,
    expected_assurance_critical_count: int = 0,
    expected_assurance_monitors: List[str] | None = None,
    battery: float | None = None,
    altitude_m: float = 10.0,
    live_mode: bool = False,
    live_connected: bool = False,
    assigned_override: List[str] | None = None,
) -> Dict:
    swarm = SwarmManager()
    drone = swarm.fleet[drone_id]
    if battery is not None:
        drone.battery = battery
    drone.altitude_m = altitude_m
    drone.status = "assigned"
    drone.target = (target["lat"], target["lng"])
    drone.waypoints = [(target["lat"], target["lng"])]
    drone.mission_target = (target["lat"], target["lng"])
    drone.live_connected = live_connected
    swarm.live_mode = live_mode

    program = compile_mission_program(command, intent, target, [drone], live_mode=live_mode, signer=logger.signer)
    safety_report = validate_mission_program(program, {drone_id: (drone.lat, drone.lng)})
    assigned = assigned_override or [drone_id]
    response = {
        "assigned": assigned,
        "intents": [intent],
        "target_resolution": [{"lat": target["lat"], "lng": target["lng"], "source": "fixture", "label": intent.get("target_zone")}],
        "parser_summary": {"modes": ["fixture"], "fallback_used": False},
        "mission_programs": [program],
        "safety_reports": [safety_report],
        "execution_results": [{"executed": False, "mode": "scenario_fixture", "safety": safety_report}],
        "plan_summary": {
            "scenario_id": scenario_id,
            "safety_passed": safety_report.get("passed"),
            "selected_drones": assigned,
        },
        "status": "executed" if safety_report.get("passed") else "not_executed",
        "confirmed": True,
        "message": f"Scenario fixture {scenario_id}",
    }
    fleet_snapshot = swarm.get_fleet_state()
    assurance = evaluate_runtime_assurance(response, fleet_snapshot)
    response["assurance_events"] = assurance["events"]
    response["assurance_summary"] = assurance["summary"]
    evidence = logger.record_confirmed_mission(
        {
            "plan_id": f"plan-{scenario_id}",
            "command": command,
            "created_at": time.time(),
            "scenario_id": scenario_id,
        },
        response,
        operator_state={
            "active": intent.get("target_reference") == "operator",
            "operator_lat": target["lat"] if intent.get("target_reference") == "operator" else None,
            "operator_lon": target["lng"] if intent.get("target_reference") == "operator" else None,
            "operator_heading": 0 if intent.get("target_reference") == "operator" else None,
        },
        fleet_snapshot=fleet_snapshot,
    )
    return {
        "scenario_id": scenario_id,
        "description": description,
        "evidence_id": evidence["evidence_id"],
        "path": evidence["path"],
        "expected_pass": expected_pass,
        "expected_failure_reasons": expected_failure_reasons or [],
        "expected_assurance_critical_count": expected_assurance_critical_count,
        "expected_assurance_monitors": expected_assurance_monitors or [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Shepherd-AI signed scenario evidence fixtures.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Output evidence directory.")
    parser.add_argument("--test-key", default=None, help="Optional test-only signing key for deterministic local fixtures.")
    args = parser.parse_args()

    signer = SignatureManager(key=args.test_key) if args.test_key else None
    result = generate_scenario_records(args.output, signer=signer)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
