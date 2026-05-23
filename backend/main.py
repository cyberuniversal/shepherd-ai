from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import httpx
import time
import uuid

try:
    from backend.action_script import synthesize_action_script
    from backend.assurance import evaluate_runtime_assurance
    from backend.assurance_report import generate_assurance_report
    from backend.brain import MissionParser
    from backend.controller import SwarmManager
    from backend.evidence_log import EvidenceLogger
    from backend.evidence_replay import EvidenceReplayHarness
    from backend.gazetteer import get_known_location_map, resolve_place_name
    from backend.mission_program import compile_mission_program
    from backend.parser_shadow_candidates import generate_parser_shadow_candidates
    from backend.parser_shadow_report import generate_parser_shadow_report
    from backend.priority import apply_priority_assessment
    from backend.safety import validate_mission_program
    from backend.scenario_regression import ScenarioRegressionRunner, run_scenario_regression
    from backend.spatial import detect_relative_direction, resolve_relative_target
    from backend.targeting import apply_target_metadata
except ImportError:
    from action_script import synthesize_action_script
    from assurance import evaluate_runtime_assurance
    from assurance_report import generate_assurance_report
    from brain import MissionParser
    from controller import SwarmManager
    from evidence_log import EvidenceLogger
    from evidence_replay import EvidenceReplayHarness
    from gazetteer import get_known_location_map, resolve_place_name
    from mission_program import compile_mission_program
    from parser_shadow_candidates import generate_parser_shadow_candidates
    from parser_shadow_report import generate_parser_shadow_report
    from priority import apply_priority_assessment
    from safety import validate_mission_program
    from scenario_regression import ScenarioRegressionRunner, run_scenario_regression
    from spatial import detect_relative_direction, resolve_relative_target
    from targeting import apply_target_metadata

app = FastAPI(
    title="Shepherd-AI",
    description="Intelligent Drone Swarm Orchestration Layer",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

parser = MissionParser()
swarm = SwarmManager()
evidence_logger = EvidenceLogger()

# ─── Request Models ───────────────────────────────────────────────────────────

class CommandInput(BaseModel):
    command: str
    selected_drones: list[str] = []

class DroneIdInput(BaseModel):
    drone_id: str

class TemperatureInput(BaseModel):
    temp: float

class GpsDeniedInput(BaseModel):
    enabled: bool

class LiveModeInput(BaseModel):
    enabled: bool

class DroneConnectInput(BaseModel):
    drone_id: str
    address: str

class SitlConnectInput(BaseModel):
    drone_id: str = "alpha-1"
    address: str = "udp://:14540"
    enable_live: bool = True

class OperatorStateInput(BaseModel):
    operator_lat: float | None = None
    operator_lon: float | None = None
    operator_heading: float | None = None
    accuracy_m: float | None = None
    heading_source: str = "device"
    active: bool = True

class MissionPlanRef(BaseModel):
    plan_id: str

# Local gazetteer seed for offline target resolution. Larger map indexes should
# be provided through SHEPHERD_GAZETTEER_PATH, not online geocoding at dispatch.

OPERATOR_STATE = {
    "active": False,
    "operator_lat": None,
    "operator_lon": None,
    "operator_heading": None,
    "accuracy_m": None,
    "heading_source": None,
    "updated_at": None,
}

MISSION_PLAN_TTL_SECONDS = 10 * 60
PENDING_MISSION_PLANS = {}
DISPATCHABLE_MISSION_ACTIONS = {"scout", "recon", "secure", "rendezvous", "patrol"}

RIYADH_CENTER = (24.7136, 46.6753)
RIYADH_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_CACHE_TTL_SECONDS = 10 * 60
LAST_WEATHER_FETCH = 0.0

async def refresh_riyadh_weather(force: bool = False) -> dict:
    """Sync backend ambient temperature from live Riyadh weather."""
    global LAST_WEATHER_FETCH

    now = time.time()
    if not force and LAST_WEATHER_FETCH and now - LAST_WEATHER_FETCH < WEATHER_CACHE_TTL_SECONDS:
        return {
            "temp": swarm.ambient_temp,
            "source": swarm.ambient_temp_source,
            "updated_at": swarm.ambient_temp_updated_at,
            "wind_speed_ms": swarm.wind_speed_ms,
            "wind_direction_deg": swarm.wind_direction_deg,
            "cached": True,
        }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                RIYADH_WEATHER_URL,
                params={
                    "latitude": RIYADH_CENTER[0],
                    "longitude": RIYADH_CENTER[1],
                    "current_weather": "true",
                },
                timeout=5.0,
            )
            res.raise_for_status()
            data = res.json()
            current_weather = data.get("current_weather", {})
            temp = current_weather.get("temperature")
            if temp is None:
                raise ValueError("Weather response did not include current temperature")

        wind_speed_kmh = float(current_weather.get("windspeed") or 0.0)
        wind_direction = float(current_weather.get("winddirection") or 0.0)
        swarm.set_weather(float(temp), wind_speed_ms=wind_speed_kmh / 3.6, wind_direction_deg=wind_direction, source="riyadh_live")
        LAST_WEATHER_FETCH = now
        return {
            "temp": swarm.ambient_temp,
            "source": swarm.ambient_temp_source,
            "updated_at": swarm.ambient_temp_updated_at,
            "wind_speed_ms": swarm.wind_speed_ms,
            "wind_direction_deg": swarm.wind_direction_deg,
            "cached": False,
        }
    except Exception as e:
        print(f"Riyadh weather sync failed: {e}")
        return {
            "temp": swarm.ambient_temp,
            "source": swarm.ambient_temp_source,
            "updated_at": swarm.ambient_temp_updated_at,
            "wind_speed_ms": swarm.wind_speed_ms,
            "wind_direction_deg": swarm.wind_direction_deg,
            "cached": True,
            "error": "weather_sync_failed",
        }

@app.on_event("startup")
async def sync_weather_on_startup():
    await refresh_riyadh_weather(force=True)

def _operator_state_ready() -> bool:
    return bool(
        OPERATOR_STATE.get("active")
        and OPERATOR_STATE.get("operator_lat") is not None
        and OPERATOR_STATE.get("operator_lon") is not None
        and OPERATOR_STATE.get("operator_heading") is not None
    )

def _relative_target_database() -> dict:
    excluded = {"riyadh"}
    seen_coords = set()
    targets = {}
    for name, coords in get_known_location_map().items():
        if name in excluded:
            continue
        rounded = (round(coords[0], 5), round(coords[1], 5))
        if rounded in seen_coords:
            continue
        seen_coords.add(rounded)
        targets[name] = coords
    return targets

def _resolve_operator_position_target() -> tuple[float, float]:
    if not _operator_state_ready():
        raise HTTPException(
            status_code=409,
            detail="Operator Link is required for commands that target the commander position. Enable OP LINK first.",
        )

    swarm._think(
        f"OPERATOR LINK: target_reference=operator resolved to live commander position "
        f"({OPERATOR_STATE['operator_lat']:.6f}, {OPERATOR_STATE['operator_lon']:.6f}).",
        "decision",
    )
    return (OPERATOR_STATE["operator_lat"], OPERATOR_STATE["operator_lon"])

def _operator_position_target_detail() -> dict:
    lat, lng = _resolve_operator_position_target()
    return {
        "resolved": True,
        "lat": lat,
        "lng": lng,
        "source": "operator_link",
        "label": "operator_current_position",
        "target_reference": "operator",
        "operator_heading": OPERATOR_STATE.get("operator_heading"),
        "operator_accuracy_m": OPERATOR_STATE.get("accuracy_m"),
        "operator_updated_at": OPERATOR_STATE.get("updated_at"),
    }

async def resolve_target_detail(zone_name: str) -> dict:
    zone_lower = str(zone_name).lower().strip()
    if not zone_lower or zone_lower == "unknown":
        return {
            "resolved": False,
            "source": "local_gazetteer",
            "label": zone_lower or "unknown",
            "query": zone_name,
            "reason": "missing_target",
            "candidates": [],
        }

    relative_direction = detect_relative_direction(zone_lower)
    if relative_direction:
        if not _operator_state_ready():
            raise HTTPException(
                status_code=409,
                detail="Operator Link is required for relative commands like 'front of me'. Enable OP LINK first.",
            )

        target = resolve_relative_target(
            (OPERATOR_STATE["operator_lat"], OPERATOR_STATE["operator_lon"]),
            OPERATOR_STATE["operator_heading"],
            _relative_target_database(),
            direction=relative_direction,
        )
        if not target:
            raise HTTPException(
                status_code=404,
                detail=f"No known target found {relative_direction} of operator heading {OPERATOR_STATE['operator_heading']:.0f} degrees.",
            )

        swarm._think(
            f"OPERATOR LINK: '{zone_name}' resolved to {target['name'].upper()} "
            f"({target['distance_m']:.0f}m away, bearing {target['bearing_deg']:.0f}°).",
            "decision",
        )
        return {
            "resolved": True,
            "lat": target["lat"],
            "lng": target["lng"],
            "source": "operator_heading_geometry",
            "label": target["name"],
            "relative_direction": relative_direction,
            "bearing_deg": target["bearing_deg"],
            "distance_m": target["distance_m"],
            "operator_heading": OPERATOR_STATE.get("operator_heading"),
        }

    result = resolve_place_name(zone_name)
    if not result.get("resolved"):
        return result
    return result

async def resolve_target(zone_name: str) -> tuple:
    detail = await resolve_target_detail(zone_name)
    if not detail.get("resolved", True) or detail.get("lat") is None or detail.get("lng") is None:
        raise HTTPException(
            status_code=422,
            detail=f"Target '{zone_name or 'unknown'}' could not be resolved by the local gazetteer.",
        )
    return (detail["lat"], detail["lng"])

def _clone_swarm_for_preview() -> SwarmManager:
    preview = SwarmManager()
    preview.live_mode = swarm.live_mode
    preview.ambient_temp = swarm.ambient_temp
    preview.ambient_temp_source = swarm.ambient_temp_source
    preview.ambient_temp_updated_at = swarm.ambient_temp_updated_at
    preview.wind_speed_ms = swarm.wind_speed_ms
    preview.wind_direction_deg = swarm.wind_direction_deg
    preview.gps_denied = swarm.gps_denied
    preview._thinking_log = []
    preview.protocol = None

    for drone_id, source in swarm.fleet.items():
        target = preview.fleet.get(drone_id)
        if not target:
            continue
        target.lat = source.lat
        target.lng = source.lng
        target.battery = source.battery
        target.status = source.status
        target.target = tuple(source.target) if source.target else None
        target.waypoints = [tuple(waypoint) for waypoint in source.waypoints]
        target._waypoint_index = source._waypoint_index
        target.mission_target = tuple(source.mission_target) if source.mission_target else None
        target.altitude_m = source.altitude_m
        target.current_priority = source.current_priority
        target.mission_start_time = source.mission_start_time
        target.nav_state.gps_available = source.nav_state.gps_available
        target.nav_state.position_source = source.nav_state.position_source
        target.nav_state.position_confidence = source.nav_state.position_confidence
        target.nav_state.drift_accumulated_m = source.nav_state.drift_accumulated_m
        target.nav_hold = source.nav_hold
        target.comms_status = source.comms_status
        target.mesh_route = list(source.mesh_route)
        target.signal_strength = source.signal_strength
        target.rotor_speed = source.rotor_speed
        target.home = tuple(source.home)
        target.live_connected = source.live_connected
        target.live_address = source.live_address
        target.live_last_telemetry_at = source.live_last_telemetry_at
        target.flight_mode = source.flight_mode
    return preview


def _dedupe_thinking(entries: list[dict]) -> list[dict]:
    deduped = []
    seen = set()
    for entry in entries:
        key = (entry.get("time"), entry.get("message"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


async def _resolve_intent_target(intent: dict) -> tuple[dict, dict]:
    if "target_coords" in intent:
        target_lat = intent["target_coords"]["lat"]
        target_lng = intent["target_coords"]["lng"]
        return {
            "resolved": True,
            "lat": target_lat,
            "lng": target_lng,
            "source": "explicit_coordinates",
            "label": "coordinates",
        }, {"lat": target_lat, "lng": target_lng}

    if intent.get("target_reference") == "operator":
        resolution_detail = _operator_position_target_detail()
        return resolution_detail, {"lat": resolution_detail["lat"], "lng": resolution_detail["lng"]}

    resolution_detail = await resolve_target_detail(intent.get("target_zone", ""))
    if not resolution_detail.get("resolved", True):
        return resolution_detail, None
    return resolution_detail, {"lat": resolution_detail["lat"], "lng": resolution_detail["lng"]}


async def _build_mission_from_intents(
    command: str,
    selected_drones: list[str],
    intents: list[dict],
    working_swarm: SwarmManager,
    execute: bool,
) -> dict:
    all_assigned = []
    all_thinking = []
    target_coords = []
    mission_programs = []
    action_scripts = []
    execution_results = []
    safety_reports = []
    target_resolution = []
    multi_intent = len(intents) > 1

    for raw_intent in intents:
        intent = apply_target_metadata(apply_priority_assessment(command, raw_intent))
        action = str(intent.get("action", "scout")).strip().lower()
        combined_drones = set(intent.get("explicit_drones", []))
        if not multi_intent:
            combined_drones.update(selected_drones)

        if action == "return":
            assigned_drones, thinking = working_swarm.recall_drones(
                drone_ids=list(combined_drones) if combined_drones else None
            )
            all_assigned.extend(assigned_drones)
            all_thinking.extend(thinking)
            target_coords.append(None)
            target_resolution.append({"source": "return_to_launch", "label": "home"})
            drones = [working_swarm.fleet[d_id] for d_id in assigned_drones if d_id in working_swarm.fleet]
            program = compile_mission_program(command, intent, None, drones, working_swarm.live_mode)
            action_script = synthesize_action_script(program)
            program_to_execute = action_script.get("compiled_program", program)
            safety_report = validate_mission_program(
                program_to_execute,
                {drone.id: (drone.lat, drone.lng) for drone in drones},
            )
            safety_reports.append(safety_report)
            mission_programs.append(program_to_execute)
            action_scripts.append(action_script)
            if execute and safety_report.get("passed"):
                execution_results.append(await working_swarm.execute_mission_program(program_to_execute))
            elif execute:
                execution_results.append({"executed": False, "mode": "safety_reject", "safety": safety_report})
            else:
                execution_results.append({"executed": False, "mode": "pending_confirmation"})
            continue

        if action not in DISPATCHABLE_MISSION_ACTIONS:
            reason = (
                f"Intent action '{action}' is not a dispatchable movement mission. "
                "No drones allocated; deterministic backend requires an explicit handler before dispatch."
            )
            working_swarm._think(f"MISSION BLOCKED: {reason}", "warning")
            all_thinking.extend(working_swarm.get_thinking_log(last_n=1))
            target_coords.append(None)
            target_resolution.append({
                "source": "non_dispatchable_intent",
                "label": intent.get("target_zone", "unknown"),
                "action": action,
                "reason": reason,
            })
            safety_reports.append({
                "passed": False,
                "safe": False,
                "issues": [reason],
                "checks": ["dispatchable intent action"],
                "engine": "deterministic_intent_gate",
            })
            execution_results.append({
                "executed": False,
                "mode": "intent_reject" if execute else "pending_confirmation",
                "reason": reason,
            })
            continue

        resolution_detail, target_coord = await _resolve_intent_target(intent)
        if target_coord is None:
            reason = (
                f"Target '{resolution_detail.get('query') or resolution_detail.get('label')}' "
                f"was not resolved by the local gazetteer ({resolution_detail.get('reason', 'not_found')}). "
                "No drones allocated; add a local gazetteer entry or provide explicit coordinates."
            )
            working_swarm._think(f"MISSION BLOCKED: {reason}", "warning")
            all_thinking.extend(working_swarm.get_thinking_log(last_n=1))
            target_coords.append(None)
            target_resolution.append(resolution_detail)
            safety_reports.append({
                "passed": False,
                "safe": False,
                "issues": [reason],
                "checks": ["offline target resolution"],
                "engine": "deterministic_target_resolver",
            })
            execution_results.append({
                "executed": False,
                "mode": "target_resolution_reject" if execute else "pending_confirmation",
                "reason": reason,
            })
            continue
        target_lat = target_coord["lat"]
        target_lng = target_coord["lng"]
        drone_count = intent.get("drone_count", 1)
        pattern = intent.get("pattern", "perimeter")
        priority = intent.get("priority", "medium")
        area_size_m = intent.get("area_size_m", 200)

        assigned_drones, thinking = working_swarm.allocate_task(
            target_lat, target_lng,
            required_drones=drone_count,
            specific_drones=list(combined_drones) if combined_drones else None,
            pattern=pattern,
            priority=priority,
            area_size_m=area_size_m,
        )
        all_assigned.extend(assigned_drones)
        all_thinking.extend(thinking)
        target_coords.append(target_coord)
        target_resolution.append(resolution_detail)
        drones = [working_swarm.fleet[d_id] for d_id in assigned_drones if d_id in working_swarm.fleet]
        program = compile_mission_program(command, intent, target_coord, drones, working_swarm.live_mode)
        action_script = synthesize_action_script(program)
        program_to_execute = action_script.get("compiled_program", program)
        safety_report = validate_mission_program(
            program_to_execute,
            {drone.id: (drone.lat, drone.lng) for drone in drones},
        )
        safety_reports.append(safety_report)
        mission_programs.append(program_to_execute)
        action_scripts.append(action_script)
        if execute and safety_report.get("passed"):
            execution_results.append(await working_swarm.execute_mission_program(program_to_execute))
        elif execute:
            reason = "; ".join(safety_report.get("issues", [])) or "route failed geometric safety checks"
            all_thinking.extend(working_swarm.cancel_assignment(assigned_drones, reason))
            rejected = set(assigned_drones)
            all_assigned = [drone_id for drone_id in all_assigned if drone_id not in rejected]
            execution_results.append({"executed": False, "mode": "safety_reject", "safety": safety_report})
        else:
            execution_results.append({"executed": False, "mode": "pending_confirmation"})

    all_assigned = list(dict.fromkeys(all_assigned))
    return {
        "intent": intents[0] if intents else {},
        "intents": intents,
        "assigned": all_assigned,
        "target_coords": target_coords,
        "target_resolution": target_resolution,
        "mission_programs": mission_programs,
        "action_scripts": action_scripts,
        "execution_results": execution_results,
        "safety_reports": safety_reports,
        "parser_summary": {
            **parser.status(),
            "modes": list(dict.fromkeys(intent.get("parser", "unknown") for intent in intents)),
            "fallback_used": any(intent.get("parser") == "heuristic" for intent in intents),
        },
        "thinking": _dedupe_thinking(all_thinking),
    }


def _build_plan_summary(plan_id: str, command: str, response: dict) -> dict:
    intents = response.get("intents", [])
    target_resolution = response.get("target_resolution", [])
    target = next((item for item in target_resolution if item and item.get("lat") is not None), None)
    unresolved_target = next((item for item in target_resolution if item and item.get("resolved") is False), None)
    safety_reports = response.get("safety_reports", [])
    safety_passed = all(report.get("passed") for report in safety_reports) if safety_reports else True
    safety_issues = [issue for report in safety_reports for issue in report.get("issues", [])]
    confidence_values = []
    for intent in intents:
        try:
            confidence_values.append(float(intent.get("confidence", 0.5)))
        except (TypeError, ValueError):
            confidence_values.append(0.5)
    confidence = round(min(confidence_values), 2) if confidence_values else 0.0
    patterns = list(dict.fromkeys(intent.get("pattern", "perimeter") for intent in intents if intent.get("action") != "return"))
    primary_intent = intents[0] if intents else {}
    programs = response.get("mission_programs") or [{}]
    mode = programs[0].get(
        "mode",
        "live_mavlink" if swarm.live_mode else "digital_twin_simulation",
    )
    confirmable = bool(response.get("assigned")) and safety_passed
    target_name = target.get("label") if target else (unresolved_target.get("label") if unresolved_target else "home")
    question = primary_intent.get("clarifying_question")
    if not question and target:
        question = f"I found {target_name} at this location. Is this where you want the drones to go?"
    elif not question and unresolved_target:
        question = f"I could not resolve '{unresolved_target.get('query') or target_name}' from the local gazetteer. Add a local map entry or provide coordinates."

    return {
        "plan_id": plan_id,
        "command": command,
        "target_name": target_name,
        "target": {"lat": target["lat"], "lng": target["lng"]} if target else None,
        "target_source": target.get("source") if target else (unresolved_target.get("source") if unresolved_target else "return_to_launch"),
        "target_reference": target.get("target_reference") if target else None,
        "selected_drones": response.get("assigned", []),
        "requested_drone_count": primary_intent.get("drone_count", 1),
        "mission_pattern": " + ".join(patterns) if patterns else "return_to_launch",
        "safety_passed": safety_passed,
        "safety_issues": safety_issues,
        "estimated_execution_mode": mode,
        "needs_confirmation": True,
        "confirmable": confirmable,
        "confidence": confidence,
        "clarifying_question": question,
        "summary": (
            f"I understand you want {primary_intent.get('drone_count', 1)} drone(s) to "
            f"{primary_intent.get('action', 'execute')} at {target_name}."
        ),
    }

# ─── API Endpoints ────────────────────────────────────────────────────────────

@app.post("/api/operator/state")
async def set_operator_state(body: OperatorStateInput):
    if not body.active:
        OPERATOR_STATE.update({"active": False, "updated_at": time.time()})
        return {"operator": OPERATOR_STATE, "message": "Operator Link disabled."}

    missing = [
        field for field in ("operator_lat", "operator_lon", "operator_heading")
        if getattr(body, field) is None
    ]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing operator telemetry fields: {', '.join(missing)}")
    if not -90 <= body.operator_lat <= 90:
        raise HTTPException(status_code=422, detail="operator_lat out of bounds")
    if not -180 <= body.operator_lon <= 180:
        raise HTTPException(status_code=422, detail="operator_lon out of bounds")

    OPERATOR_STATE.update({
        "active": True,
        "operator_lat": body.operator_lat,
        "operator_lon": body.operator_lon,
        "operator_heading": body.operator_heading % 360,
        "accuracy_m": body.accuracy_m,
        "heading_source": body.heading_source,
        "updated_at": time.time(),
    })
    return {"operator": OPERATOR_STATE, "message": "Operator telemetry updated."}

@app.get("/api/operator/state")
async def get_operator_state():
    return {"operator": OPERATOR_STATE, "ready": _operator_state_ready()}

@app.post("/api/mission/plan")
async def create_mission_plan(cmd: CommandInput):
    intents = await parser.parse_compound_intent(cmd.command)
    preview_swarm = _clone_swarm_for_preview()
    response = await _build_mission_from_intents(
        cmd.command,
        cmd.selected_drones,
        intents,
        preview_swarm,
        execute=False,
    )
    plan_id = f"plan-{uuid.uuid4().hex[:10]}"
    plan_summary = _build_plan_summary(plan_id, cmd.command, response)
    status = "pending_confirmation" if plan_summary["confirmable"] else "blocked"
    response.update({
        "plan_id": plan_id,
        "status": status,
        "plan_summary": plan_summary,
        "message": "Mission plan ready for confirmation." if plan_summary["confirmable"] else "Mission plan created but cannot be confirmed until issues are resolved.",
    })
    PENDING_MISSION_PLANS[plan_id] = {
        "plan_id": plan_id,
        "created_at": time.time(),
        "command": cmd.command,
        "selected_drones": list(cmd.selected_drones),
        "intents": intents,
        "preview": response,
    }
    swarm._think(
        f"MISSION PLAN: {plan_id} {'ready for confirmation' if plan_summary['confirmable'] else 'blocked'}; "
        f"LLM/parser output remains intent-only, deterministic safety owns dispatch.",
        "decision" if plan_summary["confirmable"] else "critical",
    )
    return response


@app.post("/api/mission/confirm")
async def confirm_mission_plan(body: MissionPlanRef):
    plan = PENDING_MISSION_PLANS.get(body.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Mission plan not found or already closed.")
    if time.time() - plan["created_at"] > MISSION_PLAN_TTL_SECONDS:
        PENDING_MISSION_PLANS.pop(body.plan_id, None)
        raise HTTPException(status_code=410, detail="Mission plan expired. Build a fresh plan before dispatch.")

    preview_summary = plan.get("preview", {}).get("plan_summary", {})
    if not preview_summary.get("confirmable"):
        raise HTTPException(status_code=409, detail="Mission plan is blocked and cannot be confirmed.")

    response = await _build_mission_from_intents(
        plan["command"],
        plan["selected_drones"],
        plan["intents"],
        swarm,
        execute=True,
    )
    plan_summary = _build_plan_summary(body.plan_id, plan["command"], response)
    PENDING_MISSION_PLANS.pop(body.plan_id, None)
    response.update({
        "plan_id": body.plan_id,
        "status": "executed" if plan_summary["safety_passed"] and response.get("assigned") else "not_executed",
        "confirmed": True,
        "plan_summary": plan_summary,
        "message": f"Mission confirmed. {len(response.get('assigned', []))} drones tasked.",
    })
    fleet_snapshot = swarm.get_fleet_state()
    assurance = evaluate_runtime_assurance(response, fleet_snapshot)
    response["assurance_events"] = assurance["events"]
    response["assurance_summary"] = assurance["summary"]
    try:
        response["evidence"] = evidence_logger.record_confirmed_mission(
            {**plan, "plan_id": body.plan_id},
            response,
            operator_state=OPERATOR_STATE.copy(),
            fleet_snapshot=fleet_snapshot,
        )
        swarm._think(
            f"EVIDENCE LOG: {response['evidence']['evidence_id']} persisted for confirmed mission {body.plan_id}.",
            "decision",
        )
    except Exception as exc:
        response["evidence"] = {"recorded": False, "error": str(exc)}
        swarm._think(f"EVIDENCE LOG FAILED: {exc}", "critical")
    return response


@app.post("/api/mission/cancel")
async def cancel_mission_plan(body: MissionPlanRef):
    plan = PENDING_MISSION_PLANS.pop(body.plan_id, None)
    if not plan:
        raise HTTPException(status_code=404, detail="Mission plan not found or already closed.")
    swarm._think(f"MISSION PLAN: {body.plan_id} cancelled by operator before dispatch.", "info")
    return {"plan_id": body.plan_id, "cancelled": True, "message": "Mission plan cancelled before dispatch."}


@app.post("/api/command")
async def process_command(cmd: CommandInput):
    intents = await parser.parse_compound_intent(cmd.command)
    response = await _build_mission_from_intents(cmd.command, cmd.selected_drones, intents, swarm, execute=True)
    response["message"] = f"{len(intents)} sub-command{'s' if len(intents) != 1 else ''} parsed. {len(response.get('assigned', []))} drones tasked."
    return response

@app.post("/api/environment")
async def set_environment(body: TemperatureInput):
    thinking = swarm.set_ambient_temp(body.temp, source="manual")
    return {
        "message": f"Ambient temperature set to {body.temp}°C",
        "throttling": body.temp > 45.0,
        "thinking": thinking
    }

@app.get("/api/weather/riyadh")
async def get_riyadh_weather(force: bool = False):
    weather = await refresh_riyadh_weather(force=force)
    return weather

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "shepherd-ai-backend"}

@app.get("/api/parser/status")
async def get_parser_status():
    return await parser.refresh_status()

@app.post("/api/gps-denied")
async def set_gps_denied(body: GpsDeniedInput):
    thinking = swarm.set_gps_denied(body.enabled)
    return {
        "message": "GPS-denied fallback enabled." if body.enabled else "GPS restored.",
        "gps_denied": body.enabled,
        "thinking": thinking
    }

@app.post("/api/live-mode")
async def set_live_mode(body: LiveModeInput):
    swarm.live_mode = body.enabled
    swarm._think(
        "LIVE MODE enabled. MAVLink bridge will receive future mission commands." if body.enabled else "Simulation mode enabled. Digital twin movement restored.",
        "warning" if body.enabled else "info"
    )
    return {"live_mode": swarm.live_mode, "thinking": swarm.get_thinking_log(last_n=5)}

@app.get("/api/drone/status")
async def get_drone_bridge_status():
    state = swarm.get_fleet_state()
    return {
        "live_mode": swarm.live_mode,
        "bridge": state["stats"].get("bridge"),
        "live_connected_drones": state["stats"].get("live_connected_drones", []),
    }

async def _connect_live_drone(drone_id: str, address: str) -> dict:
    if not swarm.bridge:
        raise HTTPException(status_code=503, detail="Drone bridge unavailable")
    if drone_id not in swarm.fleet:
        raise HTTPException(status_code=404, detail="Drone not found in fleet registry")
    try:
        await swarm.bridge.connect(drone_id, address)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail=f"Timed out waiting for MAVLink system at {address}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to connect drone: {e}")

    swarm.mark_live_connected(drone_id, address)
    swarm._think(f"LIVE LINK: {drone_id.upper()} connected at {address}.", "decision")
    return {"connected": True, "drone_id": drone_id, "address": address, "bridge": swarm.bridge.status()}

@app.post("/api/drone/connect")
async def connect_drone(body: DroneConnectInput):
    try:
        return await asyncio.wait_for(_connect_live_drone(body.drone_id, body.address), timeout=12.0)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail=f"Timed out waiting for MAVLink system at {body.address}")

@app.post("/api/drone/sitl/connect")
async def connect_px4_sitl(body: SitlConnectInput):
    try:
        result = await asyncio.wait_for(_connect_live_drone(body.drone_id, body.address), timeout=12.0)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail=f"Timed out waiting for PX4 SITL at {body.address}. Start PX4 SITL first, then try again.")
    if body.enable_live:
        swarm.live_mode = True
        swarm._think("PX4 SITL link established. LIVE MODE enabled for future mission dispatch.", "warning")
    return {**result, "live_mode": swarm.live_mode, "sitl": True}
      
@app.post("/api/crash")
async def simulate_crash(body: DroneIdInput):
    message, thinking = swarm.report_drone_lost(body.drone_id)
    return {"message": message, "thinking": thinking}

@app.post("/api/revive")
async def revive_drone(body: DroneIdInput):
    message, thinking = swarm.revive_drone(body.drone_id)
    return {"message": message, "thinking": thinking}

@app.get("/api/thinking")
async def get_thinking_log():
    return {"thinking_log": swarm.get_thinking_log()}

@app.get("/api/evidence")
async def list_evidence(limit: int = 25):
    return {"records": evidence_logger.list_records(limit=max(1, min(int(limit), 100)))}

@app.get("/api/evidence/{evidence_id}")
async def get_evidence_record(evidence_id: str):
    try:
        return evidence_logger.read_record(evidence_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Evidence record not found.")

@app.get("/api/evidence/{evidence_id}/verify")
async def verify_evidence_record(evidence_id: str):
    try:
        return evidence_logger.verify_record(evidence_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Evidence record not found.")

@app.get("/api/evidence/{evidence_id}/replay")
async def replay_evidence_record(evidence_id: str):
    try:
        return EvidenceReplayHarness(evidence_logger).replay(evidence_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Evidence record not found.")

@app.get("/api/research/scenario-regression")
async def run_research_scenario_regression(limit: int = 100, include_cases: bool = True, manifest: str | None = None):
    safe_limit = max(1, min(int(limit), 1000))
    if manifest:
        return run_scenario_regression(limit=safe_limit, manifest_path=manifest, include_cases=include_cases)
    return ScenarioRegressionRunner(evidence_logger).run(limit=safe_limit, include_cases=include_cases)


@app.get("/api/research/assurance-report")
async def run_research_assurance_report(limit: int = 100, include_records: bool = True):
    return generate_assurance_report(
        limit=max(1, min(int(limit), 1000)),
        include_records=include_records,
        evidence_logger=evidence_logger,
    )


@app.get("/api/research/parser-shadow-report")
async def run_research_parser_shadow_report(limit: int = 100, include_records: bool = True):
    return generate_parser_shadow_report(
        limit=max(1, min(int(limit), 1000)),
        include_records=include_records,
        evidence_logger=evidence_logger,
    )


@app.get("/api/research/parser-shadow-candidates")
async def run_research_parser_shadow_candidates(limit: int = 100, include_matches: bool = False):
    return generate_parser_shadow_candidates(
        limit=max(1, min(int(limit), 1000)),
        include_matches=include_matches,
        evidence_logger=evidence_logger,
    )

# ─── WebSocket for real-time fleet state ──────────────────────────────────────

@app.websocket("/ws/fleet")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    if swarm.ambient_temp_source == "default":
        await refresh_riyadh_weather(force=True)
    try:
        while True:
            if swarm.ambient_temp_source == "riyadh_live":
                await refresh_riyadh_weather()
            if swarm.live_mode:
                await swarm.sync_live_telemetry()
            swarm.step_simulation()
            state = swarm.get_fleet_state()
            state["thinking_log"] = swarm.get_thinking_log(last_n=10)
            state["operator"] = OPERATOR_STATE.copy()
            await websocket.send_json(state)
            await asyncio.sleep(1) # Send update every 1 second
    except WebSocketDisconnect:
        print("Client disconnected from WebSocket")
