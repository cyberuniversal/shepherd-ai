# Week 7 Safety, Feedback, and Integration Protocol

## Why This Comes Next

The roadmap places feedback, safety, and integration immediately after the
vision milestone. Weeks 2 through 6 now expose bounded intent, grounding,
planning, scheduling, and perception artifacts. Week 7 must gate scheduled
missions before any simulated execution and must not delegate safety decisions
to a language model.

The literature review supports this separation. TACOS uses a supervisor over
current swarm state, Swarm-Steward validates proposed actions against external
constraints, CommandSwarm blocks malformed or unauthorized actions, and
SkySim separates high-level language reasoning from deterministic safety
enforcement.

## Objective

Implement a deterministic pre-execution gate that:

- turns ambiguous or unresolved grounding into an operator clarification,
- emits ordered workflow feedback,
- validates battery, restricted-area, altitude, and availability evidence for
  every scheduled assignment,
- blocks execution when a check fails or cannot be evaluated,
- stores the complete workflow, raw checks, and aggregate evaluation results.

## Baseline and Data

The baseline is the existing deterministic pipeline:

1. `deterministic_v3` typed-command intent extraction,
2. explicit-map grounding and clarification,
3. Week 4 mission planning,
4. Week 5 `least_loaded` scheduling,
5. the Week 7 deterministic safety policy.

Development inputs are synthetic and explicitly labeled:

- map: `datasets/maps/shepherd_test_map_v1.csv`,
- fleet: `datasets/drones/week5_three_drone_fleet_v1.json`,
- policy: `datasets/safety/week7_safety_policy_v1.json`,
- cases: `datasets/safety/week7_safety_cases_v1.jsonl`.

The roadmap does not specify battery or altitude thresholds. The tracked policy
therefore records `25%` minimum battery, `60 m` maximum altitude, and `30 m`
default mission altitude as synthetic development assumptions. They are not
legal limits, hardware specifications, or safety guarantees. Command-specific
altitude ceilings are enforced in addition to the policy maximum.

## Checks

Each assignment receives exactly four roadmap checks:

- `availability`: the assigned drone exists in current state and has an allowed
  status,
- `battery`: current battery is at or above the policy threshold,
- `altitude`: the requested/default altitude satisfies the policy and any
  normalized command ceiling,
- `restricted_area`: the target exists, is flyable, does not require clearance,
  and does not have a blocked map role.

Missing current drone or map evidence produces `not_evaluated`, never a pass.
Failed checks produce `rejected`; unavailable evidence or unassigned tasks
produce `incomplete`. Both block progress.

## Evaluation

The 12 registered development cases cover:

- a safe two-drone mission,
- low battery after scheduling,
- the exact battery threshold,
- a restricted target,
- altitude above policy,
- the exact policy altitude boundary,
- a command-specific altitude ceiling,
- a post-schedule availability change,
- no idle scheduling resource,
- ambiguous and unresolved grounding that require clarification,
- a flyable target with a referenced obstacle, while explicitly recording that
  route intersection is not evaluated.

Metrics are expected-status accuracy, failed-category agreement, and counts of
passed, failed, and unavailable checks. These are synthetic branch-coverage
metrics, not physical safety performance.

## Completion Criteria

This initial Week 7 slice succeeds when:

- all 12 registered cases produce their expected workflow status,
- every scheduled assignment contains all four roadmap check categories,
- ambiguous grounding stops before planning,
- failed or unavailable safety evidence stops before simulated execution,
- schedule-based status updates are labeled as simulated,
- raw case outputs and aggregate summaries are stored separately from claims.

Week 7 is complete for roadmap advancement only when the separate completion
audit also passes and preserves the research limitations below. The current
stored development evaluation matches all 12 expected statuses and failure
categories. The completion audit permits advancement with no blockers while
deferring mission-specific imagery to the roadmap's Week 8 scenario rather
than fabricating observations.

## Known Limitations

- No route geometry or restricted-area intersection test exists because the
  current planner does not generate trajectories.
- No collision avoidance, weather, communications, dynamics, or physical
  flight validation exists.
- Schedule-derived status updates are simulation records, not observed flight
  telemetry.
- Mission-specific vision execution and final mission reporting remain Week 8
  work unless a bounded Week 7 integration contract is added first.
