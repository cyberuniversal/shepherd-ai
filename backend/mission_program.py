import hashlib
import json
import time
import uuid
from typing import Dict, List, Optional, Tuple


MISSION_LANGUAGE = "SHEPHERD-IR/2.0"
SCHEMA_VERSION = "2.0"
ALLOWED_FACADE_OPS = ["ARM", "TAKEOFF", "GOTO", "HOLD", "RTL", "LAND"]
SAFETY_MONITORS = [
    "geofence_monitor",
    "altitude_envelope_monitor",
    "pairwise_separation_monitor",
    "battery_reserve_monitor",
    "localization_health_monitor",
    "link_health_monitor",
]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _mission_digest(bundle: Dict) -> str:
    encoded = json.dumps(bundle, sort_keys=True, separators=(",", ":"), default=str)
    return _sha256_text(encoded)


def _confidence(intent: Dict) -> float:
    try:
        return round(max(0.0, min(float(intent.get("confidence", 0.75)), 1.0)), 2)
    except (TypeError, ValueError):
        return 0.75


def _intent_contract(intent: Dict, target_coords: Optional[Dict]) -> Dict:
    confidence = _confidence(intent)
    slots = {
        "target_zone": intent.get("target_zone"),
        "target_reference": intent.get("target_reference"),
        "target_coords": target_coords,
        "pattern": intent.get("pattern", "perimeter"),
        "priority": intent.get("priority", "medium"),
        "drone_count": intent.get("drone_count", 1),
        "area_size_m": intent.get("area_size_m", 200),
    }
    return {
        "verb": intent.get("action", "scout"),
        "slots": slots,
        "confidence": confidence,
        "ambiguity": round(1.0 - confidence, 2),
        "needs_confirmation": bool(intent.get("needs_confirmation", True)),
        "clarifying_question": intent.get("clarifying_question"),
        "parser": intent.get("parser", "unknown"),
    }


def _waypoint_steps(waypoints: List[Tuple[float, float]], altitude_m: float) -> List[Dict]:
    return [
        {
            "op": "GOTO",
            "lat": round(lat, 7),
            "lng": round(lng, 7),
            "altitude_m": round(altitude_m, 1),
            "acceptance_radius_m": 3.0,
            "transport": "MAVSDK.action.goto_location",
        }
        for lat, lng in waypoints
    ]


def compile_drone_program(drone, intent: Dict, source_prompt: str) -> Dict:
    """Compile a single drone's digital-twin state into drone-readable IR."""
    altitude_m = getattr(drone, "altitude_m", 10.0)
    action = intent.get("action", "scout")

    if action == "return":
        steps = [
            {"op": "RTL", "transport": "MAVSDK.action.return_to_launch"},
        ]
    else:
        waypoints = drone.waypoints or ([drone.target] if drone.target else [])
        steps = [
            {"op": "ARM", "transport": "MAVSDK.action.arm"},
            {"op": "TAKEOFF", "altitude_m": round(altitude_m, 1), "transport": "MAVSDK.action.takeoff"},
            *_waypoint_steps(waypoints, altitude_m),
            {"op": "HOLD", "duration_s": 10, "transport": "autopilot.position_hold"},
        ]

    return {
        "drone_id": drone.id,
        "program_id": f"prog-{drone.id}-{uuid.uuid4().hex[:8]}",
        "source_prompt": source_prompt,
        "intent": {
            "action": action,
            "target_zone": intent.get("target_zone"),
            "pattern": intent.get("pattern", "perimeter"),
            "priority": intent.get("priority", "medium"),
        },
        "preconditions": {
            "battery_min_percent": 15.0,
            "gps_required": True,
            "armed_required": False,
            "mavlink_required_for_live": True,
        },
        "steps": steps,
        "compiled_transport": "MAVLink via MAVSDK",
    }


def compile_mission_program(
    source_prompt: str,
    intent: Dict,
    target_coords: Optional[Dict],
    drones: List,
    live_mode: bool,
) -> Dict:
    """Compile natural-language intent into a validated mission program bundle."""
    drone_programs = [compile_drone_program(drone, intent, source_prompt) for drone in drones]
    total_steps = sum(len(program["steps"]) for program in drone_programs)
    selected_vehicles = [program["drone_id"] for program in drone_programs]
    confirmation_required = bool(intent.get("needs_confirmation", True))
    constraints = {
        "max_altitude_m": 120.0,
        "min_altitude_m": 1.0,
        "battery_reserve_pct": 15.0,
        "nav_mode": "gnss",
        "comms_policy": "connected",
        "confirmation_required": confirmation_required,
        "live_dispatch_requested": bool(live_mode),
        "allowed_facade_ops": ALLOWED_FACADE_OPS,
    }

    bundle = {
        "language": MISSION_LANGUAGE,
        "schema_version": SCHEMA_VERSION,
        "mission_id": f"mission-{uuid.uuid4().hex[:10]}",
        "compiled_at": time.time(),
        "source": {
            "modality": "text",
            "utterance_hash": _sha256_text(source_prompt),
            "operator_id": "local_operator",
        },
        "source_prompt": source_prompt,
        "intent_contract": _intent_contract(intent, target_coords),
        "target": target_coords,
        "mode": "live_mavlink" if live_mode else "digital_twin_simulation",
        "constraints": constraints,
        "allocation": {
            "baseline_allocator": "distance_energy_heuristic_v1",
            "learned_ranker": None,
            "selected_vehicles": selected_vehicles,
            "confidence": _confidence(intent),
        },
        "assurance": {
            "preconditions": [
                "operator_confirmation_required",
                "battery_reserve_ok",
                "nav_quality_ok",
                "airspace_bounds_ok",
                "link_policy_ok",
                "facade_ops_whitelisted",
            ],
            "monitors": SAFETY_MONITORS,
            "fallback_policy": "hold_then_rtl",
            "runtime_contracts": [
                "LLM output is intent-only",
                "Mission preview is non-mutating",
                "Live dispatch requires connected MAVLink vehicle",
                "All movement commands pass geometric safety validation",
                "All live commands pass through MAVSDKFacade",
            ],
        },
        "provenance": {
            "model_versions": {
                "intent": intent.get("parser", "unknown"),
                "allocator": "distance_energy_heuristic_v1",
                "safety": "geometric_sandbox_v1",
                "transport": "mavsdk_facade_v1",
            },
            "release_digest": "local-dev",
            "signature": None,
        },
        "compiler_pipeline": [
            "natural_language_prompt",
            "MissionParser intent JSON",
            "SwarmManager allocation + safety checks",
            "SHEPHERD-IR v2 mission bundle",
            "MAVSDK/MAVLink transport commands",
            "autopilot flight controller action",
        ],
        "safety_guards": [
            "battery reserve check",
            "altitude deconfliction",
            "runtime proximity monitor",
            "GPS confidence monitor",
            "mesh route monitor",
        ],
        "drone_programs": drone_programs,
        "summary": {
            "drone_count": len(drone_programs),
            "step_count": total_steps,
            "transport": "MAVSDK/MAVLink",
            "selected_vehicles": selected_vehicles,
            "confirmation_required": confirmation_required,
        },
    }
    bundle["mission_digest"] = _mission_digest(bundle)
    return bundle
