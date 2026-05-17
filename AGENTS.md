# Repository Instructions

Shepherd-AI is a research project for an offline-first, real-drone swarm command layer. Do not frame the project around event presentations or as a software-only flight environment. PX4 SITL and the digital twin are validation harnesses only.

## Core Architecture

- The LLM must never directly control drones.
- The LLM/parser may only output bounded intent JSON.
- Deterministic backend code owns target resolution, swarm allocation, safety checks, human confirmation, SHEPHERD-IR compilation, live preflight readiness checks, and MAVSDK/MAVLink dispatch.
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
- Confirmed missions should write signed evidence records. Runtime evidence JSON belongs under `evidence/` by default and should not be committed.
- Evidence replay should verify signatures, mission digests, recorded fleet snapshots, selected-drone consistency, and current deterministic safety checks.
- Scenario regression should treat signed evidence as release checks and fail on integrity, consistency, or safety replay regressions. Manifest-aware runs may pass known off-nominal failures only when observed reasons and assurance monitor expectations match the manifest.
- Generated off-nominal scenario evidence belongs under `.tmp_scenarios/` or another ignored path and should not be committed.
- Runtime assurance events are report-only unless a future safety review explicitly authorizes blocking or automatic fallback behavior.
- Assurance reports must remain read-only over evidence records and must not dispatch MAVSDK commands.
- Mission-command datasets are for parser training/evaluation only; trained models still output bounded intent JSON and never dispatch. Dataset rows should preserve train/eval/holdout split labels and clarification expectations. Keep `seed.jsonl` as the compact smoke-test gate and `benchmark.jsonl` as the larger evaluation/training benchmark. Treat `adversarial_holdout.jsonl` as evaluation-only data; do not tune deterministic parser behavior directly against it unless a row is deliberately promoted into seed or benchmark data.
- Keep `targeted_augmentation.jsonl` train-only. It may be generated from failure-analysis categories and appended with `--augmentation`, but it must not contain adversarial holdout rows or be treated as a promotion/evaluation gate.
- Learned-parser artifacts and reports belong under `.tmp_models/` by default and should not be committed. Learned parser adapters must preserve bounded intent JSON and `dispatch_authority=false`.
- PyTorch/transformer training dependencies belong in `backend/requirements-train.txt` and are optional; do not add heavyweight ML packages to the core backend requirements unless runtime use explicitly needs them.
- Learned parser candidates must pass `backend.parser_promotion` threshold and contract checks before any runtime integration work. Use `--candidate-type transformer-model --model-dir ...` for trained transformer directories.
- Use `backend.parser_failure_analysis` reports to guide dataset expansion; do not tune directly against adversarial holdout rows.
- Local signing keys belong in `.shepherd/` or an environment variable. Never commit signing keys.
- When adding learned modules, keep them behind typed contracts and deterministic safety gates.
