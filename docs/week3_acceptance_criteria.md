# Week 3 Acceptance Criteria

## Scope

These criteria define the current Week 3 completion gate for Shepherd-AI command grounding and map representation.

They apply to the current synthetic/custom Week 3 map and grounding datasets. They do not establish real-world grounding accuracy, physical-drone readiness, route safety, or planner correctness.

## Required Artifacts

Week 3 requires:

- an explicit map dataset with documented IDs, names, coordinates, aliases, map roles, flyability metadata, and clearance metadata,
- CSV map loading,
- GeoJSON Point loading,
- basic GeoJSON Polygon exterior-ring loading,
- deterministic grounding outputs with `grounded`, `ambiguous`, `unresolved`, and `not_provided` statuses,
- explicit clarification artifacts for ambiguous and unresolved examples,
- label validation for grounding evaluation datasets,
- map coverage auditing,
- reproducible raw outputs under `outputs/evaluations/`,
- Markdown reports under `reports/`,
- tests for the implemented behaviors.

## Synthetic Gate Thresholds

For the current synthetic Week 3 gate:

- exact record accuracy across every current synthetic grounding evaluation must be `1.0`,
- reference accuracy across every current synthetic grounding evaluation must be `1.0`,
- every current grounding dataset validation must contain at least one record,
- the current main synthetic map coverage report must cover every main-map record,
- the current main synthetic map coverage report must have `0` warnings,
- ambiguous references must exist in the synthetic label validations,
- unresolved references must exist in the synthetic label validations,
- the main synthetic map validation must include at least one restricted-area record and one obstacle record,
- the synthetic region GeoJSON validation must include at least one polygon record.

## Advancement Rule

Passing the synthetic gate is not, by itself, permission to move to Week 4.

Under the current project rule, Week 3 advancement also depends on resolving or explicitly deferring the research blockers listed by `reports/week3_completion_gate_audit.md`.

## Current Research Blockers

At the time this document was added, the remaining research blockers are:

- no human-collected Week 3 grounding benchmark,
- no real-world grounding evaluation.

Real or public map provenance is explicitly deferred for Week 3 in `docs/week3_research_deferrals.md`.
