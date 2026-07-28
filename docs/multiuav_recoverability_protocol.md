# MultiUAV Recoverability And Resource-Conflict Protocol

## Purpose

This policy determines whether a removed fact supports `CLARIFY`, remains
recoverable under the AGENT contract, or is the planner's responsibility. It
also limits `BLOCK` labels to fleet conflicts with no allowed recovery.

The policy runs before five-variant generation. It does not automatically
approve generated wording.

The repository literature-to-implementation rules require ambiguous semantic
grounding to fail explicitly or request clarification, while the reviewed
closed-loop systems support observation and state checking before execution.
Accordingly, this policy does not treat missing observable world state as
missing operator intent.

## Missing-Information Rule

A missing-information derivative may be labelled `CLARIFY` only when it removes
an explicit operator requirement:

- required UAV identity or count;
- destination or waypoint coordinates;
- altitude, direction, distance, or duration;
- message payload or recipient;
- target reference;
- formation assignment; or
- coverage threshold.

The following omissions do not support `CLARIFY`:

- current UAV ID, battery, status, or position already visible in context;
- target IDs, target positions, or obstacle geometry recoverable through an
  allowed nearby-observation endpoint while a semantic reference remains; and
- generic UAV assignment, API selection, route construction, or intermediate
  waypoints that belong to the validated planner.

Removing both a runtime identifier and its semantic reference is different: no
observation can determine which operator-selected object was intended, so
clarification is allowed.

## Resource-Conflict Rule

`BLOCK` is allowed only when:

1. an explicitly required UAV is absent, or the visible fleet is smaller than
   an explicit minimum requirement; and
2. the common AGENT action contract cannot register a replacement UAV.

The first dataset version must not create `BLOCK` solely from low battery, busy
status, route obstruction, or a runtime target ID that can be discovered.
Charging, waiting/replanning, obstacle-aware routing, and local perception are
allowed recovery mechanisms.

For generic tasks requiring at least one UAV, an empty visible fleet is an
irrecoverable cardinality conflict. Counterfactual resource contexts may
therefore contain an empty `drones` list even though every authentic source
session contains drones.

## Source Audit

`scripts/audit_multiuav_recoverability.py` checks all 1,473 retained source
tasks. It inventories conservative operator-fact candidates without editing
instructions. It then constructs temporary counterfactual fleet contexts and
requires the policy to justify `BLOCK` for each one.

The committed result is
`datasets/multiuav_plat/recoverability_audit_v1.json`. The result is a policy
and candidate-coverage audit, not a derived dataset or evaluation result.

## Review Boundary

Automatic generation remains draft construction. Reviewers must verify that:

- only one intended fact changed;
- restored wording adds exactly that fact plus unavoidable grammar repair;
- no remaining observation or planning path recovers the removed fact;
- the resource mutation removes every valid UAV option; and
- no hidden benchmark field appears in a model-visible context.
