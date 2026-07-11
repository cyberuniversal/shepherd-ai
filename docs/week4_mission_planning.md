# Week 4 Mission Planning

## Scope

Week 4 starts the roadmap item "Mission Planning." The current implementation converts validated Week 3 grounding output into inspectable task sequences and explicit NetworkX-backed dependency graphs for later scheduling. Observation commands include the roadmap-required sequence of takeoff, fly-to, capture images, planned vision-model task, save results, and return. Constraint-bearing commands get an explicit `review_constraints` step before takeoff.

This is not route optimization, multi-drone allocation, actual Week 6 vision inference, safety validation, simulation execution, or physical drone control.

## Why This Comes Next

Week 3 now produces bounded grounded map objects with location IDs, coordinates, geometry metadata, flyability flags, and clearance flags. The planner consumes those objects and creates an explicit sequence of high-level tasks such as validation, takeoff, fly-to, scan or inspect, capture images, run a planned vision-model task, save results, and return.

This follows the literature-driven rule that language interpretation and grounding should be separated from execution authority. The planner emits structured steps; it does not execute arbitrary generated code.

## Current Interface

Primary module:

- `src/shepherd_ai/mission_planning.py`

Primary script:

- `scripts/plan_mission.py`
- `scripts/evaluate_mission_planning.py`
- `scripts/render_mission_flow.py`
- `scripts/audit_week4_completion.py`

Primary structures:

- `MissionPlanStep`: one high-level task with an action, dependencies, optional map object, expected output, and notes.
- `MissionPlan`: a serializable plan with status, scheduling readiness, original intent, primary map object, steps, issues, and notes.
- `MissionPlanValidation`: deterministic contract check for plan status, dependencies, required actions, map-object coordinates, and blocked-plan rules.

Primary function:

- `plan_grounded_mission(grounded_intent)`
- `validate_mission_plan(plan)`
- `mission_plan_task_graph(plan)`
- `mission_plan_networkx_graph(plan)`
- `mission_plan_mermaid(plan)`

## Reproducible Examples

Plan one grounded command:

```powershell
python scripts/plan_mission.py --command "Scan the crops in the north field." --map datasets/maps/shepherd_test_map_v1.csv --output outputs/evaluations/week4_plan_north_field_example.json
```

Create a blocked plan for ambiguous grounding:

```powershell
python scripts/plan_mission.py --command "Check if there is any traffic on the road." --map datasets/maps/shepherd_test_map_v1.csv --output outputs/evaluations/week4_plan_ambiguous_road_blocked.json
```

Evaluate planning over the human-written grounding benchmark:

```powershell
python scripts/evaluate_mission_planning.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/human_grounding_benchmark_v1.jsonl --output outputs/evaluations/week4_planning_human_grounding_benchmark_v1.json
```

Evaluate focused Week 4 planning cases:

```powershell
python scripts/evaluate_mission_planning.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/week4_planning_cases_v1.jsonl --output outputs/evaluations/week4_planning_cases_v1.json
```

Render a mission-flow diagram:

```powershell
python scripts/render_mission_flow.py --command "Scan the crops in the north field." --map datasets/maps/shepherd_test_map_v1.csv --output outputs/diagrams/week4_plan_north_field_flow.md
```

Audit Week 4 completion gates:

```powershell
python scripts/audit_week4_completion.py --human-planning-evaluation outputs/evaluations/week4_planning_human_grounding_benchmark_v1.json --focused-planning-evaluation outputs/evaluations/week4_planning_cases_v1.json --flow-diagram outputs/diagrams/week4_plan_north_field_flow.md --acceptance-criteria docs/week4_acceptance_criteria.json --research-deferrals docs/week4_research_deferrals.json --json-output outputs/evaluations/week4_completion_gate_audit.json --markdown-output reports/week4_completion_gate_audit.md
```

## Current Evaluation

Current evaluation artifact:

- `outputs/evaluations/week4_planning_human_grounding_benchmark_v1.json`

Current result:

- Records: 22
- Planned records: 20
- Blocked records: 2
- Ready-for-scheduling records: 20
- Valid plan-contract records: 22
- Expected status matches: 22 / 22
- Expected status accuracy: 1.0
- Required action accuracy: 1.0
- Required issue accuracy: 1.0

Focused Week 4 planning-case result:

- Dataset: `datasets/maps/week4_planning_cases_v1.jsonl`
- Output: `outputs/evaluations/week4_planning_cases_v1.json`
- Records: 7
- Planned records: 5
- Blocked records: 2
- Valid plan-contract records: 7
- Expected status matches: 7 / 7
- Required action matches: 7 / 7
- Required issue matches: 7 / 7

Completion-gate result:

- Output: `outputs/evaluations/week4_completion_gate_audit.json`
- Report: `reports/week4_completion_gate_audit.md`
- Flow diagram: `outputs/diagrams/week4_plan_north_field_flow.md`
- Advancement allowed: `true`
- Decision: `week4_complete_for_advancement_to_week5_scheduling`
- Blockers: none

Interpretation:

The planner correctly creates task sequences for commands with grounded map objects, includes the roadmap-required observation steps (`capture_images`, `run_vision_model`, `save_observation_results`, and return), adds constraint-review steps when constraints are present, carries referenced obstacle/restricted metadata forward as issues, and blocks commands whose grounding is ambiguous or has no grounded map reference. Every generated planned or blocked artifact passes the deterministic plan contract. This is a planning-gate evaluation, not execution success.

## Known Limitations

- The planner is deterministic and rule-based.
- It uses NetworkX for the dependency graph representation, but does not run graph search or route optimization.
- It does not optimize routes or compute paths.
- It does not allocate drones.
- It does not run a simulator.
- It does not run the actual computer-vision model; `run_vision_model` is a planned Week 4 task record for the later Week 6 vision module.
- It does not validate battery, altitude, restricted-area safety, or collision constraints.
- Restricted and obstacle map records are carried forward as issues for later safety validation, not rejected as unsafe by this module.
- Constraint review is a planner contract step only; it does not decide whether a constrained mission is safe.
- The current evaluation uses the custom synthetic map and human-written commands over that map. It is not real-world mission planning evidence.

## Completion Criteria For This Slice

This Week 4 slice is complete when:

- valid grounded commands produce serializable task sequences,
- ambiguous or unresolved commands produce blocked plans,
- plan steps preserve grounded map IDs and coordinates,
- task-graph nodes and dependency edges are explicit,
- plan validation checks dependency consistency and required action coverage,
- observation commands include `capture_images`, `run_vision_model`, `save_observation_results`, and return steps,
- constraint-bearing commands include an explicit `review_constraints` step,
- restricted and clearance metadata is preserved as planner issues,
- a CLI can write raw planning artifacts,
- a planning evaluation writes raw metrics,
- a mission-flow diagram is generated,
- a completion audit records acceptance criteria, explicit deferrals, and advancement status,
- tests cover successful and blocked planning behavior.
