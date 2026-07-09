# Week 5 Acceptance Criteria

Scope: synthetic Week 5 multi-drone scheduling gate.

This is not an execution benchmark. Passing this gate means the repository has a reproducible scheduler slice that satisfies the roadmap's Week 5 deliverables over the current custom synthetic map and simulated drone fleet.

Required gates:

- Three simulated drones are present.
- Planned mission tasks are assigned automatically.
- No default example task remains unassigned.
- The primary example uses all three drones.
- A multi-drone command is replicated into multiple schedulable tasks.
- Assignment tables are written.
- Allocation visualization is written.
- At least three deterministic strategy baselines are compared.
- Shared scheduling metrics are recorded.
- Notebook 5 runs the scheduler and the completion audit.

This gate does not claim route optimization, safety validation, simulated execution, physical-drone control, or a universally optimal allocation strategy.
