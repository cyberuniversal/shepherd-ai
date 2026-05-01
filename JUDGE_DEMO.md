# Judge Demo Flow

Use this as the short presentation path for Shepherd-AI.

## One Sentence

Shepherd-AI turns natural language intent into a safe drone mission program, then dispatches it to a simulated or real autopilot through MAVSDK/MAVLink.

## Prompt To Drone

```text
Human prompt
-> intent JSON
-> target resolution
-> drone assignment
-> geometric safety check
-> SHEPHERD-IR mission program
-> MAVSDK facade
-> MAVLink
-> PX4 autopilot
-> drone movement and telemetry
```

## Demo Script

1. Start Shepherd-AI with `npm run dev`.
2. Enable `OP LINK` and show the cyan operator marker on the map.
3. Send `Bring two drones to me`.
4. Open the `Program` tab and show `Prompt-To-Drone Proof`:
   - Parser mode.
   - Target source: `operator_link`.
   - Safety result.
   - Execution mode.
5. Send `send alpha-1 to KAFD` and show:
   - `SHEPHERD-IR` steps.
   - Disposable action script sandbox.
   - Drone path on the map.
6. If PX4 SITL is running, click `PX4 SITL` and repeat `send alpha-1 to KAFD`.
7. Show the bridge card changing from simulation to MAVSDK/PX4 status.

## What To Tell Judges

The important point is that the LLM/parser does not fly the drone directly. It only produces structured intent. Shepherd-AI then applies deterministic allocation and safety checks before generating `SHEPHERD-IR`. Only safe high-level operations pass through the MAVSDK facade to PX4.

## What Is Real Today

- Browser voice/text command input.
- Operator GPS/heading through OP LINK.
- Deterministic target resolution for landmarks, coordinates, operator location, and front/left/right references.
- Fleet assignment, energy checks, deconfliction, GPS-denied simulation, and mesh simulation.
- Geometric safety sandbox.
- `SHEPHERD-IR` mission compilation.
- MAVSDK/PX4 bridge path for SITL/live autopilots.

## What Requires PX4 Running

The `PX4 SITL` button only connects to PX4. It does not start PX4. Start PX4 separately using `PX4_SITL_SETUP.md`, then connect from the dashboard.
