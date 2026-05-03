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
-> human confirmation
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
4. Show the Plan Preview panel:
   - Target source: `operator_link`.
   - Cyan operator marker on the map.
   - Selected drones.
   - Safety result.
   - `Confirm Mission` button.
5. Click `Confirm Mission` and watch the drones move.
6. Open the `Program` tab and show `Prompt-To-Drone Proof`:
   - Parser mode.
   - LLM online/model/fallback status.
   - Target resolution.
   - Safety result.
   - Execution mode.
7. Send `Bring two drones to Al Nada` and show:
   - Intent JSON target: `al nada`.
   - Amber plan marker on the map before dispatch.
   - Confirmation gate before movement.
8. Send `send alpha-1 to KAFD` and show:
   - `SHEPHERD-IR` steps.
   - Disposable action script sandbox.
   - Drone path on the map.
9. If PX4 SITL is running, click `PX4 SITL` and repeat `send alpha-1 to KAFD`.
10. Show the bridge card changing from simulation to MAVSDK/PX4 status.

## What To Tell Judges

The important point is that the LLM/parser does not fly the drone directly. It only produces structured intent. Shepherd-AI then applies deterministic target resolution, allocation, safety checks, and a human confirmation gate before generating or dispatching `SHEPHERD-IR`. Only safe high-level operations pass through the MAVSDK facade to PX4.

## What Is Real Today

- Browser voice/text command input.
- Plan-first mission preview with confirm/cancel flow.
- Operator GPS/heading through OP LINK.
- Deterministic target resolution for landmarks, coordinates, operator location, and front/left/right references.
- Fleet assignment, energy checks, deconfliction, GPS-denied simulation, and mesh simulation.
- Geometric safety sandbox.
- `SHEPHERD-IR` mission compilation.
- MAVSDK/PX4 bridge path for SITL/live autopilots.

## What Requires PX4 Running

The `PX4 SITL` button only connects to PX4. It does not start PX4. Start PX4 separately using `PX4_SITL_SETUP.md`, then connect from the dashboard.
