# MultiUAV Intervention Pilot Protocol

## Scope

The active intervention-generation pass is a training-only pilot. It selects
two eligible tasks from each of the 15 scenario/difficulty strata, producing 30
source clusters and 150 draft cases.

Version 2 uses the seed `shepherd-multiuav-intervention-pilot-v2`. In every
stratum it selects one explicit-UAV-identity intervention and one
coverage-threshold intervention. The result is 15 clusters of each supported
fact kind. Calibration and test tasks remain excluded so template debugging
cannot inspect or tune on the locked evaluation splits.

Version 1 is preserved as diagnostic evidence. External feedback correctly
identified its 29-to-1 fact-kind imbalance and its overly wide review packet.
It is superseded and must not be reviewed or used for model inference.

## Five Draft Cases

Each selected source task produces:

1. the canonical upstream instruction with proposed `EXECUTE`;
2. the selected official alias with proposed `EXECUTE`;
3. a template-generated missing-fact instruction with proposed `CLARIFY`;
4. its matched restored-fact instruction with proposed `EXECUTE`; and
5. the canonical instruction plus an irrecoverable fleet patch with proposed
   `BLOCK`.

All decisions remain `pending_human_review`. They are not gold labels.

## Resource Conflicts

An identity case removes exactly the UAV identities required by that source
task. A generic-fleet case removes every visible UAV and registers a minimum
required count of one. The validator recomputes the conflict after applying the
patch and rejects patches that target different UAVs, fail to justify `BLOCK`,
or disagree with stored conflict metadata.

The review packet reports base and case fleet counts/statuses plus the exact
task-specific conflict mutation. It does not substitute one generic reason for
the applied mutation.

## Leakage Control

One shared context is stored per cluster, but its instruction field contains
only `__CASE_INSTRUCTION__`. `materialize_case_context()` injects exactly the
selected case instruction and then applies its registered context patch. This
prevents the canonical instruction from restoring a fact removed in the
missing-information case.

The deterministic validator rejects incomplete or reordered clusters,
duplicate identifiers, invalid decisions, unsupported context patches,
privileged fields, mismatched resource conflicts, and registered wording
corruptions. The artifact validator reconstructs every selected cluster from
the pinned archive and confirms the split, selection, strata, review packet,
and hashes.

## Compact Review

The version 2 CSV contains one row per case, not four instruction variants in
one cluster row. Each row contains:

- a stable case and cluster identifier;
- one exact instruction to judge;
- concise entity, UAV-status, and intervention summaries;
- the proposed decision and automatic structural-validation status; and
- blank human-review fields.

Blank reviewer fields are expected in the frozen template. No reviewer identity
or judgment has been fabricated.

## Negative Controls

Known-bad inputs are kept outside the pilot. The synthetic negative-control
audit mutates a complete cluster into an incomplete cluster and changes a
resource patch to target the wrong UAV. Both must be rejected. These probes are
validator tests, not collected cases, training data, or evaluation data.

## Active Artifacts

- Draft clusters: `datasets/multiuav_plat/intervention_pilot_v2.json`
- Generation summary: `datasets/multiuav_plat/intervention_pilot_summary_v2.json`
- Validation record: `datasets/multiuav_plat/intervention_pilot_validation_v2.json`
- Compact review packet: `reports/multiuav_intervention_pilot_review_v2.csv`
- Negative controls:
  `datasets/multiuav_plat/intervention_validator_negative_controls_v1.json`

The pilot must not enter model inference or publication summaries.

```powershell
python scripts/validate_multiuav_intervention_pilot.py `
  --output datasets/multiuav_plat/intervention_pilot_validation_v2.json

python scripts/audit_multiuav_intervention_validator.py `
  --output datasets/multiuav_plat/intervention_validator_negative_controls_v1.json
```
