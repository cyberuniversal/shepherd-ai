# Week 4 Acceptance Criteria

Scope: `synthetic_week4_completion_gate_v1`.

These criteria apply only to the high-level mission-planning slice over the current custom synthetic map and grounding outputs. They are not scheduling, route-feasibility, safety, simulation-execution, or physical-drone criteria.

Required thresholds:

- At least one evaluated record.
- Expected plan-status accuracy must be `1.0`.
- Required action coverage must be `1.0`.
- Required issue coverage must be `1.0`.
- Valid plan-contract fraction must be `1.0`.

The completion audit also requires planned and blocked cases, the roadmap scan sequence (`takeoff`, `fly_to`, `capture_images`, `run_vision_model`, save results, and return), explicit task graphs, a mission-flow diagram, a constraint-review case, preserved restricted or clearance issues, and scheduling readiness that matches plan status.
