# Repository Instructions

Shepherd-AI is a research project for an offline-first, real-drone swarm command layer. Do not frame the project around event presentations or as a software-only flight environment. PX4 SITL and the digital twin are validation harnesses only.

## Core Architecture

- The LLM must never directly control drones.
- The LLM/parser may only output bounded intent JSON.
- Deterministic backend code owns target resolution, swarm allocation, safety checks, human confirmation, SHEPHERD-IR compilation, and MAVSDK/MAVLink dispatch.
- Real drone dispatch goes through the constrained MAVSDK facade only.
- Keep allowed high-level facade operations limited to `ARM`, `TAKEOFF`, `GOTO`, `HOLD`, `RTL`, and `LAND` unless a safety review explicitly expands the set.

## Development Commands

- Backend commands should use the project virtual environment:
  - `.\.venv\Scripts\python.exe -m backend.smoke_tests`
  - `.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload`
- Frontend checks:
  - `npm --prefix frontend run lint`
  - `npm --prefix frontend run build`
- Full-stack dev:
  - `npm run dev`

## Product Direction

- Prefer plan-first APIs: `/api/mission/plan`, `/api/mission/confirm`, `/api/mission/cancel`.
- Treat `/api/command` as legacy/internal scripted execution.
- PX4 SITL controls should only connect to an already-running PX4 endpoint; never start PX4 from the dashboard.
- Do not add unvalidated perception-driven reroutes or UI/docs that imply perception capabilities without real telemetry and validation.
- When adding learned modules, keep them behind typed contracts and deterministic safety gates.
