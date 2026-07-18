# Week 8 Interactive 3D Design

## Scope Decision

The interactive 3D interface is a user-requested Week 8 extension. The roadmap
requires a Python software simulation and visualization but does not require a
3D engine. Three.js is used only as a renderer for validated Python telemetry;
the browser does not plan, schedule, bypass safety, or execute generated code.

## Interaction Contract

1. The operator enters a typed command.
2. The local Python API runs decomposition, intent extraction, grounding,
   planning, scheduling, and preflight safety.
3. Ambiguous destinations return bounded map choices and stop execution.
4. Approved schedules produce deterministic, time-stepped telemetry.
5. Three.js renders that telemetry and exposes playback and camera controls.
6. A perception target such as a car has no coordinates before a valid vision
   observation. The drone searches only within the grounded region.

## Visual System

- Full-bleed 3D canvas with compact operational rails rather than a landing
  page or dashboard card grid.
- Graphite chrome, neutral text, green nominal state, amber clarification, red
  safety block, cyan routes, and varied terrain colors.
- Maximum 6 px control and panel radius.
- Fixed top toolbar, pipeline rail, telemetry rail, and bottom command dock.
- Mobile layouts collapse stage and telemetry detail without covering the
  command workflow.

The implemented desktop and mobile verification captures are stored under
`outputs/visualizations/` with a metadata record that limits their claim scope
to interface rendering.

## Research Limits

- The scene is a deterministic 3D visualization, not aerodynamic simulation.
- Static search paths are not active collision avoidance.
- No object is displayed as found until mission imagery and a valid vision
  result exist.
- Typed interaction does not satisfy the roadmap's missing exact-scenario ASR
  requirement.
