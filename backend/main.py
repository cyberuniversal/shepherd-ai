from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import hashlib
import httpx
import time

try:
    from backend.action_script import synthesize_action_script
    from backend.brain import MissionParser
    from backend.controller import SwarmManager
    from backend.mission_program import compile_mission_program
    from backend.safety import validate_mission_program, validate_route_leg
    from backend.spatial import detect_relative_direction, resolve_relative_target
except ImportError:
    from action_script import synthesize_action_script
    from brain import MissionParser
    from controller import SwarmManager
    from mission_program import compile_mission_program
    from safety import validate_mission_program, validate_route_leg
    from spatial import detect_relative_direction, resolve_relative_target

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

class ObstacleInput(BaseModel):
    drone_id: str
    distance_m: float

# ─── Known Locations (Riyadh landmarks) ───────────────────────────────────────

KNOWN_LOCATIONS = {
    "riyadh": (24.7136, 46.6753),
    "imam university": (24.8144, 46.7027),
    "جامعة الامام": (24.8144, 46.7027),
    "airport": (24.9576, 46.7000),
    "المطار": (24.9576, 46.7000),
    "wadi hanifah": (24.6366, 46.6120),
    "وادي حنيفة": (24.6366, 46.6120),
    "kafd": (24.7610, 46.6402),
    "المركز المالي": (24.7610, 46.6402),
    "kingdom centre": (24.7114, 46.6744),
    "kingdom center": (24.7114, 46.6744),
    "al faisaliyah": (24.6906, 46.6851),
    "boulevard": (24.7675, 46.6044),
    "diriyah": (24.7335, 46.5750),
    "masmak": (24.6312, 46.7133),
    "stadium": (24.7886, 46.8396),
    "king saud university": (24.7163, 46.6190),
    "national museum": (24.6473, 46.7107),
    "ministry of defense": (24.6644, 46.7126),
    "al nada": (24.8012, 46.6808),
}

LOCATION_CACHE = {}

OPERATOR_STATE = {
    "active": False,
    "operator_lat": None,
    "operator_lon": None,
    "operator_heading": None,
    "accuracy_m": None,
    "heading_source": None,
    "updated_at": None,
}

# ─── Riyadh bounding box for fallback coords ─────────────────────────────────
RIYADH_CENTER = (24.7136, 46.6753)
RIYADH_RADIUS = 0.05  # ~5km in degrees
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
    for name, coords in KNOWN_LOCATIONS.items():
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
    if not zone_name or zone_name == "unknown":
        return {
            "lat": RIYADH_CENTER[0],
            "lng": RIYADH_CENTER[1],
            "source": "default_riyadh_center",
            "label": "riyadh_center",
        }
         
    zone_lower = str(zone_name).lower().strip()

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
            "lat": target["lat"],
            "lng": target["lng"],
            "source": "operator_heading_geometry",
            "label": target["name"],
            "relative_direction": relative_direction,
            "bearing_deg": target["bearing_deg"],
            "distance_m": target["distance_m"],
            "operator_heading": OPERATOR_STATE.get("operator_heading"),
        }
     
    # Sort keys longest-first so "kingdom centre" matches before "kingdom"
    sorted_keys = sorted(KNOWN_LOCATIONS.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if key in zone_lower:
            lat, lng = KNOWN_LOCATIONS[key]
            return {"lat": lat, "lng": lng, "source": "known_location", "label": key}
            
    # Check local cache for offline memorization
    if zone_lower in LOCATION_CACHE:
        lat, lng = LOCATION_CACHE[zone_lower]
        return {"lat": lat, "lng": lng, "source": "location_cache", "label": zone_lower}
        
    # Dynamic Geocoding via OpenStreetMap Nominatim (online fallback)
    try:
        query = f"{zone_name} Riyadh Saudi Arabia"
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "json", "limit": 1},
                headers={"User-Agent": "ShepherdAI/1.0"},
                timeout=5.0
            )
            data = res.json()
            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lng = float(data[0]["lon"])
                LOCATION_CACHE[zone_lower] = (lat, lng) # Memorize it
                print(f"Dynamically geocoded {zone_name} -> ({lat}, {lng})")
                return {"lat": lat, "lng": lng, "source": "nominatim", "label": zone_name}
    except Exception as e:
        print(f"Geocoding failed for {zone_name}: {e}")
            
    # Fallback: deterministic coordinate within Riyadh bounding box
    h = int(hashlib.sha256(zone_name.encode()).hexdigest(), 16)
    lat_offset = ((h % 100) - 50) / 1000.0 * (RIYADH_RADIUS / 0.05)
    lng_offset = (((h // 100) % 100) - 50) / 1000.0 * (RIYADH_RADIUS / 0.05)
    return {
        "lat": RIYADH_CENTER[0] + lat_offset,
        "lng": RIYADH_CENTER[1] + lng_offset,
        "source": "deterministic_fallback",
        "label": zone_name,
    }

async def resolve_target(zone_name: str) -> tuple:
    detail = await resolve_target_detail(zone_name)
    return (detail["lat"], detail["lng"])

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

@app.post("/api/obstacle")
async def report_obstacle(body: ObstacleInput):
    def validate_obstacle_reroute(drone_id: str, start: tuple, end: tuple, altitude_m: float) -> dict:
        return validate_route_leg(drone_id, start, end, altitude_m)

    result = swarm.handle_obstacle_event(
        body.drone_id,
        body.distance_m,
        route_validator=validate_obstacle_reroute,
    )
    return result

@app.post("/api/command")
async def process_command(cmd: CommandInput):
    intents = await parser.parse_compound_intent(cmd.command)
    all_assigned = []
    all_thinking = []
    target_coords = []
    mission_programs = []
    action_scripts = []
    execution_results = []
    safety_reports = []
    target_resolution = []
    multi_intent = len(intents) > 1

    for intent in intents:
        combined_drones = set(intent.get("explicit_drones", []))
        if not multi_intent:
            combined_drones.update(cmd.selected_drones)

        if intent.get("action") == "return":
            assigned_drones, thinking = swarm.recall_drones(
                drone_ids=list(combined_drones) if combined_drones else None
            )
            all_assigned.extend(assigned_drones)
            all_thinking.extend(thinking)
            target_coords.append(None)
            target_resolution.append({"source": "return_to_launch", "label": "home"})
            drones = [swarm.fleet[d_id] for d_id in assigned_drones if d_id in swarm.fleet]
            program = compile_mission_program(cmd.command, intent, None, drones, swarm.live_mode)
            action_script = synthesize_action_script(program, use_reroute=False)
            program_to_execute = action_script.get("rerouted_program", program)
            safety_report = validate_mission_program(
                program_to_execute,
                {drone.id: (drone.lat, drone.lng) for drone in drones},
            )
            program_to_execute["geometric_safety"] = safety_report
            safety_reports.append(safety_report)
            mission_programs.append(program_to_execute)
            action_scripts.append(action_script)
            if safety_report.get("passed"):
                execution_results.append(await swarm.execute_mission_program(program_to_execute))
            else:
                execution_results.append({"executed": False, "mode": "safety_reject", "safety": safety_report})
            continue

        if "target_coords" in intent:
            target_lat = intent["target_coords"]["lat"]
            target_lng = intent["target_coords"]["lng"]
            resolution_detail = {
                "lat": target_lat,
                "lng": target_lng,
                "source": "explicit_coordinates",
                "label": "coordinates",
            }
        elif intent.get("target_reference") == "operator":
            resolution_detail = _operator_position_target_detail()
            target_lat = resolution_detail["lat"]
            target_lng = resolution_detail["lng"]
        else:
            target_zone = intent.get("target_zone", "")
            resolution_detail = await resolve_target_detail(target_zone)
            target_lat = resolution_detail["lat"]
            target_lng = resolution_detail["lng"]

        drone_count = intent.get("drone_count", 1)
        pattern = intent.get("pattern", "perimeter")
        priority = intent.get("priority", "medium")
        area_size_m = intent.get("area_size_m", 200)

        assigned_drones, thinking = swarm.allocate_task(
            target_lat, target_lng,
            required_drones=drone_count,
            specific_drones=list(combined_drones) if combined_drones else None,
            pattern=pattern,
            priority=priority,
            area_size_m=area_size_m,
        )
        all_assigned.extend(assigned_drones)
        all_thinking.extend(thinking)
        target_coord = {"lat": target_lat, "lng": target_lng}
        target_coords.append(target_coord)
        target_resolution.append(resolution_detail)
        drones = [swarm.fleet[d_id] for d_id in assigned_drones if d_id in swarm.fleet]
        program = compile_mission_program(cmd.command, intent, target_coord, drones, swarm.live_mode)
        action_script = synthesize_action_script(program, use_reroute=True)
        if action_script.get("sandbox", {}).get("passed"):
            _apply_reroute_patches_to_swarm(action_script.get("reroute_patches", []))
        program_to_execute = action_script.get("rerouted_program", program)
        safety_report = validate_mission_program(
            program_to_execute,
            {drone.id: (drone.lat, drone.lng) for drone in drones},
        )
        program_to_execute["geometric_safety"] = safety_report
        safety_reports.append(safety_report)
        mission_programs.append(program_to_execute)
        action_scripts.append(action_script)
        if safety_report.get("passed"):
            execution_results.append(await swarm.execute_mission_program(program_to_execute))
        else:
            reason = "; ".join(safety_report.get("issues", [])) or "route failed geometric safety checks"
            all_thinking.extend(swarm.cancel_assignment(assigned_drones, reason))
            rejected = set(assigned_drones)
            all_assigned = [drone_id for drone_id in all_assigned if drone_id not in rejected]
            execution_results.append({"executed": False, "mode": "safety_reject", "safety": safety_report})

    all_assigned = list(dict.fromkeys(all_assigned))
    deduped_thinking = []
    seen_thinking = set()
    for entry in all_thinking:
        key = (entry.get("time"), entry.get("message"))
        if key in seen_thinking:
            continue
        seen_thinking.add(key)
        deduped_thinking.append(entry)
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
            "fallback_used": any(intent.get("parser") != "llm" for intent in intents),
        },
        "thinking": deduped_thinking,
        "message": f"{len(intents)} sub-command{'s' if len(intents) != 1 else ''} parsed. {len(all_assigned)} drones tasked."
    }


def _apply_reroute_patches_to_swarm(patches: list[dict]):
    for patch in patches:
        drone_id = patch.get("drone_id")
        drone = swarm.fleet.get(drone_id)
        patched = patch.get("patched") or {}
        original = patch.get("original") or {}
        if not drone or not patched:
            continue

        patched_waypoint = (patched["lat"], patched["lng"])
        for index, waypoint in enumerate(drone.waypoints):
            if abs(waypoint[0] - original.get("lat", waypoint[0])) < 0.000001 and abs(waypoint[1] - original.get("lng", waypoint[1])) < 0.000001:
                drone.waypoints[index] = patched_waypoint
                if index == drone._waypoint_index:
                    drone.target = patched_waypoint
                swarm._think(
                    f"OODA ACT: {drone.id.upper()} path recompiled around synthetic obstacle; waypoint {index + 1} updated.",
                    "decision"
                )
                break

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
    return parser.status()

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
