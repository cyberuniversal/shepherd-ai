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
except ImportError:
    from action_script import synthesize_action_script
    from brain import MissionParser
    from controller import SwarmManager
    from mission_program import compile_mission_program

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

async def resolve_target(zone_name: str) -> tuple:
    if not zone_name or zone_name == "unknown":
        return RIYADH_CENTER
        
    zone_lower = str(zone_name).lower().strip()
    
    # Sort keys longest-first so "kingdom centre" matches before "kingdom"
    sorted_keys = sorted(KNOWN_LOCATIONS.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if key in zone_lower:
            return KNOWN_LOCATIONS[key]
            
    # Check local cache for offline memorization
    if zone_lower in LOCATION_CACHE:
        return LOCATION_CACHE[zone_lower]
        
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
                return (lat, lng)
    except Exception as e:
        print(f"Geocoding failed for {zone_name}: {e}")
            
    # Fallback: deterministic coordinate within Riyadh bounding box
    h = int(hashlib.sha256(zone_name.encode()).hexdigest(), 16)
    lat_offset = ((h % 100) - 50) / 1000.0 * (RIYADH_RADIUS / 0.05)
    lng_offset = (((h // 100) % 100) - 50) / 1000.0 * (RIYADH_RADIUS / 0.05)
    return (RIYADH_CENTER[0] + lat_offset, RIYADH_CENTER[1] + lng_offset)

# ─── API Endpoints ────────────────────────────────────────────────────────────

@app.post("/api/command")
async def process_command(cmd: CommandInput):
    intents = await parser.parse_compound_intent(cmd.command)
    all_assigned = []
    all_thinking = []
    target_coords = []
    mission_programs = []
    action_scripts = []
    execution_results = []
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
            drones = [swarm.fleet[d_id] for d_id in assigned_drones if d_id in swarm.fleet]
            program = compile_mission_program(cmd.command, intent, None, drones, swarm.live_mode)
            action_script = synthesize_action_script(program, use_reroute=False)
            program_to_execute = action_script.get("rerouted_program", program)
            mission_programs.append(program_to_execute)
            action_scripts.append(action_script)
            execution_results.append(await swarm.execute_mission_program(program_to_execute))
            continue

        if "target_coords" in intent:
            target_lat = intent["target_coords"]["lat"]
            target_lng = intent["target_coords"]["lng"]
        else:
            target_zone = intent.get("target_zone", "")
            target_lat, target_lng = await resolve_target(target_zone)

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
        drones = [swarm.fleet[d_id] for d_id in assigned_drones if d_id in swarm.fleet]
        program = compile_mission_program(cmd.command, intent, target_coord, drones, swarm.live_mode)
        action_script = synthesize_action_script(program, use_reroute=True)
        if action_script.get("sandbox", {}).get("passed"):
            _apply_reroute_patches_to_swarm(action_script.get("reroute_patches", []))
        program_to_execute = action_script.get("rerouted_program", program)
        mission_programs.append(program_to_execute)
        action_scripts.append(action_script)
        execution_results.append(await swarm.execute_mission_program(program_to_execute))

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
        "mission_programs": mission_programs,
        "action_scripts": action_scripts,
        "execution_results": execution_results,
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

@app.post("/api/drone/connect")
async def connect_drone(body: DroneConnectInput):
    if not swarm.bridge:
        raise HTTPException(status_code=503, detail="Drone bridge unavailable")
    if body.drone_id not in swarm.fleet:
        raise HTTPException(status_code=404, detail="Drone not found in fleet registry")
    try:
        await swarm.bridge.connect(body.drone_id, body.address)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to connect drone: {e}")
    swarm._think(f"LIVE LINK: {body.drone_id.upper()} connected at {body.address}.", "decision")
    return {"connected": True, "drone_id": body.drone_id, "address": body.address}
      
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
            swarm.step_simulation()
            state = swarm.get_fleet_state()
            state["thinking_log"] = swarm.get_thinking_log(last_n=10)
            await websocket.send_json(state)
            await asyncio.sleep(1) # Send update every 1 second
    except WebSocketDisconnect:
        print("Client disconnected from WebSocket")
