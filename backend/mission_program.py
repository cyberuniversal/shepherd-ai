import time
import uuid
from typing import Dict, List, Optional, Tuple


MISSION_LANGUAGE = "SHEPHERD-IR/1.0"


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

    return {
        "language": MISSION_LANGUAGE,
        "mission_id": f"mission-{uuid.uuid4().hex[:10]}",
        "compiled_at": time.time(),
        "source_prompt": source_prompt,
        "target": target_coords,
        "mode": "live_mavlink" if live_mode else "digital_twin_simulation",
        "compiler_pipeline": [
            "natural_language_prompt",
            "MissionParser intent JSON",
            "SwarmManager allocation + safety checks",
            "SHEPHERD-IR step program",
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
        },
    }
