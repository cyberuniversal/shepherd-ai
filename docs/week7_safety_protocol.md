# Week 7 Safety, Feedback, And Integration Protocol

## Scope

Week 7 implements the roadmap's clarification dialogue, simulated mission
status updates, battery/restricted-area/altitude/availability checks, and
integration of prior modules. The literature review controls the technical
boundary: semantic interpretation remains separate from deterministic safety
and event-driven supervision, and failures preserve unfinished work.

This is a Python software simulation. It does not control physical drones or
provide a physical-flight safety guarantee.

## Architecture

1. `src/shepherd_ai/clarification_dialogue.py` validates operator choices and
   records response, confirmation, cancellation, retry, and timeout states.
2. `src/shepherd_ai/safety.py` applies the four roadmap checks, a straight-line
   circle/polygon restricted-area intersection baseline, and pairwise current
   separation checks.
3. `src/shepherd_ai/mission_supervision.py` owns mission/task lifecycle,
   confirmation, pause/resume/cancel, telemetry safety rechecks, completion,
   low-battery return requests, and hold/replan requests.
4. `src/shepherd_ai/integrated_prototype.py` connects typed or stored Whisper
   input, the selected deterministic or trained intent interface, grounding,
   planning, scheduling, safety, a bounded Week 6 artifact reference, and
   supervision.

The original schedule-derived status helper remains a projection and is not
used as completion evidence. Supervisor status comes from explicit simulated
events and telemetry snapshots.

## Policy

`datasets/safety/week7_safety_policy_v1.json` records the synthetic assumptions:

- minimum battery: `25%`,
- maximum altitude: `60 m`,
- default altitude: `30 m`,
- route clearance margin: `0 m`,
- minimum inter-drone separation: `20 m`.

These are not legal limits or hardware specifications. Command-specific
altitude ceilings are enforced in addition to the policy maximum. The policy
sensitivity study changes one threshold at a time and records decision
sequences; it does not claim to identify optimal or physically safe values.

## Stored Evidence

- Preflight: 12 registered cases, all expected workflow statuses and failed
  categories matched.
- Clarification: 4 registered stateful dialogue cases, all expected terminal
  statuses and event sequences matched.
- Route geometry: 3 registered straight-line circle/polygon cases, all expected
  decisions and intersections matched.
- Supervision: 8 registered event-driven cases, all expected final states,
  event sequences, and interventions matched. One case accepts a safe snapshot
  and rejects a later separation violation.
- Integration: 3 registered cases cover typed selected-primary intent, typed
  trained intent, and a stored Whisper prediction. All reach active supervision
  and bind the Week 6 result as development evidence only.
- Sensitivity: 4 dimensions cover battery, altitude, route margin, and
  separation. All registered decision sequences and monotonicity checks matched.

Raw inputs are under `datasets/safety/`. Full outputs are under
`outputs/evaluations/`; human-readable analyses are under `reports/`.

## Completion Decision

The corrected completion gate permits Week 8 advancement with no blockers.
This decision differs from the superseded preflight-only audit: a documented
deferral no longer counts as evidence that a capability exists.

## Limitations

- Straight-line center-to-center routes are a baseline, not route planning or
  continuous geofence enforcement.
- Pairwise position checks detect a separation violation but do not implement
  an active collision-avoidance controller or vehicle dynamics.
- Return and hold/replan outputs are intervention requests; no trajectory
  executor carries them out.
- The stored Whisper and Week 6 artifacts are consumed without rerunning their
  heavy models. The vision artifact is not imagery captured by the simulated
  mission.
- Weather, communications loss, sensor noise, and physical flight remain
  unevaluated.
- Mission-specific imagery, the complete roadmap scenario, overall execution
  time, and final mission reporting remain Week 8 work.
