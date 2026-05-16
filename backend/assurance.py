import time
from typing import Dict, List


LOCALIZATION_WARNING_THRESHOLD = 0.75
LOCALIZATION_CRITICAL_THRESHOLD = 0.5
BATTERY_MARGIN_WARNING_PCT = 5.0


def _event(
    monitor: str,
    severity: str,
    message: str,
    vehicle_id: str | None = None,
    fallback_recommendation: str = "none",
    details: Dict | None = None,
) -> Dict:
    return {
        "monitor": monitor,
        "severity": severity,
        "vehicle_id": vehicle_id,
        "message": message,
        "fallback_recommendation": fallback_recommendation,
        "details": details or {},
        "report_only": True,
        "timestamp": time.time(),
    }


def summarize_assurance_events(events: List[Dict]) -> Dict:
    severity_counts = {"info": 0, "warning": 0, "critical": 0}
    for event in events:
        severity = event.get("severity", "info")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    return {
        "report_only": True,
        "event_count": len(events),
        "severity_counts": severity_counts,
        "critical_count": severity_counts.get("critical", 0),
        "warning_count": severity_counts.get("warning", 0),
        "passed": severity_counts.get("critical", 0) == 0,
    }


def evaluate_runtime_assurance(response: Dict, fleet_snapshot: Dict | None = None) -> Dict:
    """Generate report-only runtime assurance events for a confirmed mission."""
    fleet_snapshot = fleet_snapshot or {}
    mission_programs = response.get("mission_programs", [])
    selected_drones = list(dict.fromkeys(response.get("assigned", []) or response.get("selected_drones", [])))
    fleet_by_id = {
        drone.get("id"): drone
        for drone in fleet_snapshot.get("drones", [])
        if drone.get("id")
    }

    events = []
    events.extend(_selected_vehicle_events(selected_drones, mission_programs))
    events.extend(_safety_report_events(response.get("safety_reports", [])))
    events.extend(_program_constraint_events(mission_programs, fleet_by_id))

    summary = summarize_assurance_events(events)
    return {
        "events": events,
        "summary": summary,
    }


def _selected_vehicle_events(selected_drones: List[str], mission_programs: List[Dict]) -> List[Dict]:
    program_drones = []
    for program in mission_programs:
        program_drones.extend(program.get("allocation", {}).get("selected_vehicles", []))
        program_drones.extend(
            drone_program.get("drone_id")
            for drone_program in program.get("drone_programs", [])
            if drone_program.get("drone_id")
        )
    program_drones = list(dict.fromkeys(program_drones))
    events = []

    if sorted(selected_drones) != sorted(program_drones):
        events.append(_event(
            "selected_vehicle_consistency",
            "critical",
            "Selected drones do not match SHEPHERD-IR allocated vehicles.",
            fallback_recommendation="hold_and_replan",
            details={
                "selected_drones": selected_drones,
                "program_drones": program_drones,
            },
        ))
    return events


def _safety_report_events(safety_reports: List[Dict]) -> List[Dict]:
    events = []
    for index, report in enumerate(safety_reports):
        if report.get("passed"):
            continue
        issues = report.get("issues", [])
        events.append(_event(
            "safety_replay_status",
            "critical",
            "Deterministic safety report did not pass.",
            fallback_recommendation="hold_and_replan",
            details={
                "report_index": index,
                "issues": issues,
                "checks": report.get("checks", []),
            },
        ))
    return events


def _program_constraint_events(mission_programs: List[Dict], fleet_by_id: Dict[str, Dict]) -> List[Dict]:
    events = []
    for program in mission_programs:
        constraints = program.get("constraints", {})
        battery_reserve = float(constraints.get("battery_reserve_pct", 15.0))
        min_altitude = float(constraints.get("min_altitude_m", 1.0))
        max_altitude = float(constraints.get("max_altitude_m", 120.0))
        live_dispatch_requested = bool(constraints.get("live_dispatch_requested"))

        for drone_program in program.get("drone_programs", []):
            drone_id = drone_program.get("drone_id")
            drone_snapshot = fleet_by_id.get(drone_id, {})
            events.extend(_battery_events(drone_id, drone_snapshot, battery_reserve))
            events.extend(_localization_events(drone_id, drone_snapshot))
            events.extend(_link_events(drone_id, drone_snapshot, live_dispatch_requested))
            events.extend(_altitude_events(drone_id, drone_program, min_altitude, max_altitude))
    return events


def _battery_events(drone_id: str, drone_snapshot: Dict, battery_reserve: float) -> List[Dict]:
    battery = drone_snapshot.get("battery")
    if battery is None:
        return [_event(
            "battery_reserve",
            "warning",
            "No battery snapshot was available for selected vehicle.",
            vehicle_id=drone_id,
            fallback_recommendation="verify_telemetry_before_dispatch",
        )]

    battery = float(battery)
    if battery < battery_reserve:
        return [_event(
            "battery_reserve",
            "critical",
            f"Battery {battery:.1f}% is below reserve {battery_reserve:.1f}%.",
            vehicle_id=drone_id,
            fallback_recommendation="hold_and_replan",
            details={"battery": battery, "reserve": battery_reserve},
        )]
    if battery < battery_reserve + BATTERY_MARGIN_WARNING_PCT:
        return [_event(
            "battery_reserve",
            "warning",
            f"Battery {battery:.1f}% is near reserve {battery_reserve:.1f}%.",
            vehicle_id=drone_id,
            fallback_recommendation="prefer_shorter_route_or_reserve_vehicle",
            details={"battery": battery, "reserve": battery_reserve},
        )]
    return []


def _localization_events(drone_id: str, drone_snapshot: Dict) -> List[Dict]:
    confidence = drone_snapshot.get("nav_confidence")
    if confidence is None:
        return [_event(
            "localization_confidence",
            "warning",
            "No localization confidence snapshot was available for selected vehicle.",
            vehicle_id=drone_id,
            fallback_recommendation="verify_navigation_before_dispatch",
        )]

    confidence = float(confidence)
    if confidence < LOCALIZATION_CRITICAL_THRESHOLD:
        severity = "critical"
        fallback = "hold_or_rtl"
    elif confidence < LOCALIZATION_WARNING_THRESHOLD:
        severity = "warning"
        fallback = "increase_supervision"
    else:
        return []

    return [_event(
        "localization_confidence",
        severity,
        f"Localization confidence {confidence:.2f} is below {LOCALIZATION_WARNING_THRESHOLD:.2f}.",
        vehicle_id=drone_id,
        fallback_recommendation=fallback,
        details={"confidence": confidence},
    )]


def _link_events(drone_id: str, drone_snapshot: Dict, live_dispatch_requested: bool) -> List[Dict]:
    if not live_dispatch_requested:
        return []
    if drone_snapshot.get("live_connected"):
        return []
    return [_event(
        "link_health",
        "critical",
        "Live MAVLink dispatch was requested but selected vehicle is not live-connected.",
        vehicle_id=drone_id,
        fallback_recommendation="hold_until_link_restored",
        details={"live_dispatch_requested": True},
    )]


def _altitude_events(drone_id: str, drone_program: Dict, min_altitude: float, max_altitude: float) -> List[Dict]:
    events = []
    for index, step in enumerate(drone_program.get("steps", [])):
        if step.get("op") not in ("TAKEOFF", "GOTO"):
            continue
        altitude = float(step.get("altitude_m", min_altitude))
        if min_altitude <= altitude <= max_altitude:
            continue
        events.append(_event(
            "altitude_envelope",
            "critical",
            f"Step altitude {altitude:.1f}m is outside {min_altitude:.1f}-{max_altitude:.1f}m envelope.",
            vehicle_id=drone_id,
            fallback_recommendation="hold_and_replan",
            details={
                "step_index": index,
                "op": step.get("op"),
                "altitude_m": altitude,
                "min_altitude_m": min_altitude,
                "max_altitude_m": max_altitude,
            },
        ))
    return events
