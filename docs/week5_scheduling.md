# Week 5 Multi-Drone Scheduling

Roadmap role: allocate tasks across multiple virtual drones, display assignments, implement simple scheduling logic, compare strategies, provide a scheduler notebook, create allocation visualization, and run example simulations.

## Technical Approach

Week 5 consumes Week 4 mission plans that are marked ready for scheduling. A command requesting multiple drones is expanded into multiple schedulable task replicas. The scheduler then assigns tasks to a simulated fleet of three drones.

Implemented deterministic strategies:

- `round_robin`: cycles tasks across available drones.
- `least_loaded`: chooses the drone with the lowest projected finish time.
- `nearest_available`: chooses by availability time, distance, then drone id.

The current metrics are synthetic scheduling proxies:

- assigned tasks
- unassigned tasks
- drones used
- makespan in minutes
- total active time in minutes
- total travel distance in meters
- workload range in minutes
- assignment-count range
- mean response delay in minutes

## Literature-Driven Boundaries

The literature review supports keeping scheduling separate from language interpretation, safety validation, and execution. Week 5 uses deterministic baselines instead of LLM assignment. The task-allocation review supports comparing algorithms under shared metrics, but its narrative and extracted tables conflict about which algorithm is consistently best, so Shepherd-AI does not claim a universally superior strategy.

## Reproducible Commands

Run the default Week 5 example:

```powershell
python scripts\schedule_missions.py
```

Run the Week 5 completion gate:

```powershell
python scripts\audit_week5_completion.py
```

Run focused tests:

```powershell
python -m unittest tests.test_scheduling tests.test_schedule_missions_cli tests.test_week5_completion tests.test_audit_week5_completion_cli
```

## Default Inputs

- Map: `datasets/maps/shepherd_test_map_v1.csv`
- Fleet: `datasets/drones/week5_three_drone_fleet_v1.json`
- Commands are defined in `scripts/schedule_missions.py`.

## Default Outputs

- Strategy comparison JSON: `outputs/evaluations/week5_schedule_comparison_v1.json`
- Assignment report: `reports/week5_schedule_comparison_v1.md`
- Assignment CSV: `outputs/tables/week5_assignments_least_loaded.csv`
- Allocation visualization: `outputs/visualizations/week5_drone_allocation_least_loaded.html`
- Completion audit JSON: `outputs/evaluations/week5_completion_gate_audit.json`
- Completion audit report: `reports/week5_completion_gate_audit.md`

## Current Limitations

Week 5 does not implement route optimization, collision avoidance, battery safety checks, restricted-area checks, altitude checks, real execution, physical-drone control, or computer-vision inference. Those are separate roadmap milestones.
