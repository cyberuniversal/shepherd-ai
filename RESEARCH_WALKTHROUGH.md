# Shepherd-AI Research Walkthrough

Use this as the concise system walkthrough for collaborators, advisors, or technical review.

## One Sentence

Shepherd-AI is an offline-first command layer that compiles natural-language operator intent into typed, auditable, safety-gated MAVSDK/MAVLink missions for real PX4/ArduPilot drone swarms.

## Core Pipeline

```text
human prompt
-> bounded intent JSON
-> deterministic target resolution
-> swarm allocation
-> safety and confirmation gate
-> SHEPHERD-IR v2 mission bundle
-> live preflight readiness gate
-> constrained MAVSDK facade
-> MAVLink
-> PX4/ArduPilot autopilot
-> drone movement and telemetry
```

## Key Research Claim

The LLM/parser does not fly the drone. It only proposes structured intent. Shepherd-AI then applies deterministic target resolution, allocation, safety checks, human confirmation, and live preflight readiness checks before compiling or dispatching `SHEPHERD-IR`. Only safe high-level operations pass through the MAVSDK facade.

## What Exists Now

- Browser text/voice command input.
- Plan-first mission preview with confirm/cancel flow.
- Operator GPS/heading through OP LINK.
- Deterministic target resolution for landmarks, coordinates, operator location, and front/left/right references.
- Fleet assignment, energy checks, altitude deconfliction, GPS-denied test mode, and mesh/link modeling.
- Geometric safety sandbox.
- `SHEPHERD-IR/2.0` mission bundle compilation with constraints, assurance monitors, allocation, and provenance.
- Live preflight readiness checks before MAVSDK dispatch.
- Confirmed-mission evidence records containing the IR bundle, signed digest, parser provenance, safety report, preflight result, execution result, selected drones, fleet snapshot, timestamps, and operator confirmation state.
- Evidence replay verifies record signatures, mission digests, selected-drone consistency, and current deterministic safety results against the recorded mission.
- Scenario regression turns signed evidence records into release checks so backend changes can prove they did not silently change mission safety behavior.
- Off-nominal scenario fixtures can generate ignored local evidence records for nominal, tampered, mismatch, low-battery, live-link, altitude-envelope, operator-relative, and safety-rejected replay coverage.
- Manifest-aware scenario regression reports expected failures separately from unexpected regressions and can write a JSON release-gate report.
- Runtime assurance currently emits report-only monitor events and fallback recommendations; it does not automatically trigger HOLD, RTL, or live vehicle commands.
- Assurance reports aggregate signed evidence into monitor counts, critical findings, replay status, signature status, and fallback recommendations without calling MAVSDK.
- Mission-command dataset scaffolding provides English/Arabic seed, 200+ row benchmark, train-only targeted augmentation, and adversarial holdout files, train/eval/holdout splits, and parser baseline reports before any model training starts.
- Learned-parser research scaffolding can train a local nearest-ngram baseline artifact, prepare an optional PyTorch/transformer corpus, evaluate frozen splits, append train-only failure-analysis augmentation, analyze parser failures, gate learned-artifact or transformer-model promotion, and serve predictions through strict bounded-intent adapters without live dispatch authority.
- MAVSDK/PX4 bridge path for SITL validation or live autopilots.
- Live telemetry sync into the dashboard when MAVSDK is connected.

## Research Direction

- Keep upgrading `SHEPHERD-IR` as the main typed contract between learned intent parsing and deterministic execution.
- Add stronger runtime assurance: geofence, reserve-energy, separation, localization quality, link health, and fallback policies.
- Keep deterministic allocation as the production baseline; add CBBA/auction fallback and learned rankers only as optional candidate scoring modules.
- Expand scenario regression coverage with more off-nominal records, assurance events, and release-level pass/fail reports.
- Treat perception and voice as gated cueing inputs, never as direct actuation paths.
- Grow the mission-command dataset before fine-tuning parser models. Use train-only augmentation for failure-analysis coverage, then measure against held-out command-to-intent examples, including the adversarial holdout that is not used for parser tuning.
- Run the optional transformer trainer on a capable local/edge machine after the artifact, corpus, report, and strict adapter contracts remain stable.
- Treat the parser promotion gate as the minimum bar before any learned parser candidate can be considered for runtime testing.
- Use parser failure-analysis reports to prioritize dataset expansion by target-zone, action, drone-count, language, and adversarial command class.

## Hardware Path

Start PX4 SITL or connect a real MAVLink endpoint separately, then connect Shepherd-AI:

```text
PX4 SITL:              udp://:14540
Wi-Fi MAVLink:         udp://192.168.x.x:14550
Telemetry radio/USB:   serial:///dev/ttyUSB0:57600
```

The dashboard `PX4 SITL` button only connects to an already-running endpoint. It does not start PX4.
