# PX4 SITL Setup

PX4 SITL is the software autopilot target used for validation without hardware. Shepherd-AI does not start PX4 for you; it connects to an already-running PX4 endpoint through MAVSDK/MAVLink.

## Recommended Location

Use WSL/Linux home, not the Windows-mounted project folder. Building from `/mnt/c/...` is slower and more error-prone.

```bash
cd ~
git clone https://github.com/PX4/PX4-Autopilot.git --recursive
cd PX4-Autopilot
bash ./Tools/setup/ubuntu.sh
```

Close and reopen WSL after setup, then run:

```bash
cd ~/PX4-Autopilot
make px4_sitl gz_x500
```

The first build can take a long time. CMake developer warnings about Python policy are usually harmless; the real error, if any, appears near the end of the output.

## Connect Shepherd-AI

Start Shepherd-AI:

```bash
npm run dev
```

Then in the dashboard:

1. Select `alpha-1`, or leave no drone selected to use `alpha-1` by default.
2. Click `PX4 SITL`.
3. Wait for the bridge card to show a connected drone.
4. Send a simple command such as `send alpha-1 to KAFD`.

Shepherd-AI connects to PX4 at:

```text
udp://:14540
```

If PX4 is not running, the button should timeout with a message telling you to start PX4 SITL first.

## What PX4 Does

Shepherd-AI decides the mission. PX4 flies the drone.

Shepherd-AI handles:

- Natural language command parsing.
- Drone assignment.
- Safety checks.
- `SHEPHERD-IR` mission compilation.
- MAVSDK/MAVLink dispatch.

PX4 handles:

- Arming.
- Takeoff.
- Stabilization.
- Navigation to GPS waypoints.
- Holding position.
- Return-to-launch behavior.
- Flight telemetry.
