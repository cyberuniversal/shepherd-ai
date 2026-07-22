# Week 8 2D Roadmap Resume 001

## Scope

This run resumes the roadmap's Python software simulation after the operator
discontinued the optional 3D experiments. It is a stored partial Week 8 result,
not milestone completion.

## Configuration

- Date: 2026-07-21
- Fixed command: `Send two drones north to inspect crops and one drone east to inspect irrigation.`
- Destination resolution: East Field for clause 2, retained from explicit operator confirmation
- Scheduler: `least_loaded`
- Simulator: `deterministic_2d_mission_simulator_v1`
- Time step: 0.25 simulated minutes
- Map, fleet, policy, package versions, and hashes: stored in
  `outputs/evaluations/week8_roadmap_scenario_simulation.json`

## Stored Partial Result

- Simulation status: completed
- Assignments: 3
- Simulated duration: 10.486 minutes
- Telemetry records: 43
- Minimum observed inter-drone separation: 39.955058 m
- Configured minimum separation: 20 m
- Raw telemetry:
  `outputs/evaluations/week8_roadmap_scenario_telemetry.jsonl`
- Animated map:
  `outputs/visualizations/week8_roadmap_scenario_simulation.html`

These values establish only deterministic movement-simulation behavior.

## Completion Audit

`scripts/audit_week8_completion.py` records the current decision as
`remain_on_week8_until_end_to_end_evidence_is_complete` with these blockers:

- exact-scenario ASR evidence;
- trained two-clause intent evaluation;
- mission-assigned vision evaluation;
- all five roadmap metrics;
- final raw/derived demonstration artifacts;
- explicit claim-limit fields in the absent evaluation summary.

An attempted local inference with the installed frozen Hugging Face checkpoint
did not run because the current Windows Python environment lacks Transformers,
Accelerate, and Datasets. No deterministic result was substituted. The trained
checkpoint inference remains a Colab execution step.

## Vision Uncertainty

The roadmap requests crop and irrigation inspection but does not define their
vision labels. The project will not treat VisDrone person/vehicle detections as
crop or irrigation findings. The unresolved evaluation mapping is documented
in `docs/week8_evidence_contract.md`.
