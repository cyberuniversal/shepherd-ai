# MultiUAV Intervention Pilot Protocol

## Scope

The first intervention-generation pass is a training-only pilot. It selects two
eligible tasks from each of the 15 scenario/difficulty strata, producing 30
source clusters and 150 draft cases.

Selection uses the seed `shepherd-multiuav-intervention-pilot-v1`. Calibration
and test tasks are excluded so template debugging cannot inspect or tune on the
locked evaluation splits.

## Five Draft Cases

Each selected source task produces:

1. the canonical upstream instruction with proposed `EXECUTE`;
2. the selected official alias with proposed `EXECUTE`;
3. a template-generated missing-fact instruction with proposed `CLARIFY`;
4. its matched restored-fact instruction with proposed `EXECUTE`; and
5. the canonical instruction plus an irrecoverable fleet patch with proposed
   `BLOCK`.

All decisions remain `pending_human_review`. They are not gold labels.

## Leakage Control

One shared context is stored per cluster, but its instruction field contains
only `__CASE_INSTRUCTION__`. `materialize_case_context()` injects exactly the
selected case instruction and then applies its registered context patch. This
prevents the canonical instruction from restoring a fact removed in the
missing-information case.

The deterministic validator rejects:

- partial or reordered clusters;
- duplicate case identifiers;
- canonical, missing, and restored text that are not distinct;
- context patches outside the two registered fleet mutations;
- privileged source fields at any depth;
- repeated whitespace and the known `drone the drone` corruption pattern; and
- proposed decisions inconsistent with the five-way protocol.

The artifact-level validator additionally reconstructs every stored cluster
from the pinned archive and eligibility record, confirms the deterministic
training selection, checks all 15 strata, and requires the compact review CSV
to match the unreviewed dataset exactly.

## Compact Review

The review CSV contains one row per source cluster. It includes the four text
forms, intervention summary, stable identifiers, and blank review fields. It
does not duplicate full mission contexts.

Reviewer IDs must be real pseudonyms assigned by the project team. A row is not
approved until all five validity columns and the overall review status are
completed under a registered adjudication procedure.

## Artifacts

- Draft clusters:
  `datasets/multiuav_plat/intervention_pilot_v1.json`
- Generation summary:
  `datasets/multiuav_plat/intervention_pilot_summary_v1.json`
- Validation record:
  `datasets/multiuav_plat/intervention_pilot_validation_v1.json`
- Compact review packet:
  `reports/multiuav_intervention_pilot_review_v1.csv`

The pilot must not enter model inference or publication summaries.

Re-run the independent artifact validation from the repository root:

```powershell
python scripts/validate_multiuav_intervention_pilot.py `
  --output datasets/multiuav_plat/intervention_pilot_validation_v1.json
```
