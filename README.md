# Shepherd-AI (Al-Ra'i)

Bridging the gap between strategic human intent and multi-agent execution.

## Architecture

```mermaid
flowchart LR
  A[Voice or Text Command] --> B[NLP Parser]
  B --> C[Intent JSON]
  C --> D[Swarm Allocation + Safety Checks]
  D --> E[SHEPHERD-IR Mission Program]
  E --> F[MAVSDK / MAVLink Commands]
  F --> G[PX4 / ArduPilot Autopilot]
  G --> H[Drone Motors + Telemetry]
  D --> I[Digital Twin Simulation]
  I --> J[Map + Thinking Log]
```

## Prompt To Drone

Judges should see this as a compiler pipeline, not magic:

1. The commander speaks or types natural language.
2. `backend/brain.py` parses it into structured intent JSON.
3. `backend/controller.py` allocates drones and applies battery, collision, GPS, and mesh safety checks.
4. `backend/mission_program.py` compiles the mission into `SHEPHERD-IR/1.0`, a drone-readable step program.
5. `backend/action_script.py` synthesizes a temporary Python action script through a restricted MAVSDK facade and validates it in a sandbox/static safety pass.
6. In simulation mode, the digital twin executes the same validated route visually.
7. In live mode, `backend/drone_bridge.py` maps the validated mission steps to MAVSDK/MAVLink calls like `arm`, `takeoff`, `goto_location`, and `return_to_launch`.

Example `SHEPHERD-IR` step:

```json
{
  "op": "GOTO",
  "lat": 24.761,
  "lng": 46.6402,
  "altitude_m": 10,
  "transport": "MAVSDK.action.goto_location"
}
```

The dashboard `Program` tab shows both the compiled `SHEPHERD-IR` and the generated disposable Python action script. The OODA overlay shows how synthetic sensor feedback can trigger a route recompile around an obstacle.

To connect a real PX4 SITL or MAVLink-capable drone:

```bash
curl -X POST http://localhost:8000/api/drone/connect \
  -H "Content-Type: application/json" \
  -d '{"drone_id":"alpha-1","address":"udp://:14540"}'

curl -X POST http://localhost:8000/api/live-mode \
  -H "Content-Type: application/json" \
  -d '{"enabled":true}'
```

## Quick Start

### One Command

```bash
npm run dev
```

This starts the FastAPI backend on `http://localhost:8000` and the Vite frontend on `http://localhost:5173`.

### Backend

```powershell
cd shepherd-ai
python -m venv .venv
.\.venv\Scripts\activate
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173/` in Chrome for voice input support.

## Features

- Natural language command input in English and Arabic.
- Voice input using the Web Speech API with EN/AR mode toggle.
- 13-drone fleet across Alpha, Beta, Gamma, and Delta squadrons.
- AI thinking log for transparent allocation decisions.
- Dynamic re-tasking on drone failure.
- Live Riyadh temperature sync plus thermal throttling simulation for high-temperature Saudi conditions.
- Search patterns: perimeter, lawn-mower, and spiral.
- Compound commands, e.g. `make 3 drones go to kafd and 4 to al nada`.
- Flight path lines, waypoint paths, target zones, and drone trails on the map.
- 3D map building extrusions at close zoom levels.
- GPS-denied navigation confidence, drift, hold, and autonomous RTB behavior.
- Mesh routing simulation, collision avoidance, altitude deconfliction, and battery-aware energy checks.
- Optional MAVSDK bridge scaffolding for PX4/ArduPilot SITL or real autopilots.
- SHEPHERD-IR mission program panel showing exactly what commands are sent to drones.
- Real-Time Mission Synthesis panel showing temporary Python action scripts, sandbox results, and OODA reroutes.
- Temperature slider, squadron selection, and mission manifest export.
- GPS-denied fallback simulation with dead-reckoning status banner.
- Demo Mode scripted showcase for live presentations.

## Tech Stack

- Backend: Python 3.12, FastAPI, optional Ollama local LLM.
- Frontend: React 19, Vite, MapLibre GL, shadcn-style UI primitives.
- NLP: Gemma 2B via Ollama when available, deterministic heuristic fallback otherwise.
- Drone I/O: optional MAVSDK bridge, disabled by default in simulation mode.

## Demo Commands

```text
deploy 5 drones to scan KAFD
make 3 drones go to kafd and 4 to al nada
spiral into the stadium
send beta-1 to secure the airport
recall all drones
أرسل ٥ طائرات إلى المطار
```
