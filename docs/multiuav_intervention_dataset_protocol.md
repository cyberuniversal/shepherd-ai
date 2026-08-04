# MultiUAV Full Intervention Dataset Protocol

## Scope

This stage applies the pilot-validated five-case construction to every source
task marked eligible by `task_eligibility_v1.json`. It creates an unreviewed
draft dataset and compact review packet. It does not create evaluation labels
or authorize model inference.

The pinned source contains 1,500 tasks. Twenty-seven tasks remain excluded for
the reasons stored in the eligibility manifest. The resulting draft contains
1,473 clusters and 7,365 cases: 899/290/284 clusters and 4,495/1,450/1,420
cases in train/calibration/test. Every source cluster remains within its
session-assigned split.

## Construction

Each eligible source task produces the same five linked cases used by the
approved pilot template:

1. canonical `EXECUTE`;
2. official-alias `EXECUTE`;
3. missing-fact `CLARIFY`;
4. restored-fact `EXECUTE`; and
5. resource-conflict `BLOCK`.

These are deterministic controlled-derivative labels, not human-authored gold
labels. The balanced 30-cluster pilot provides stratified expert quality
control of the construction method. Its case-level approvals are not copied
onto newly generated rows, and the project does not claim that all 7,365 cases
were independently reviewed.

## Reproducible Commands

```powershell
python scripts/build_multiuav_intervention_dataset.py `
  --dataset-output datasets/multiuav_plat/intervention_dataset_v1.json `
  --review-output reports/multiuav_intervention_review_v1.csv `
  --summary-output datasets/multiuav_plat/intervention_dataset_summary_v1.json

python scripts/validate_multiuav_intervention_dataset.py `
  --output datasets/multiuav_plat/intervention_dataset_validation_v1.json
```

The validator reconstructs every eligible cluster from the pinned archive,
requires exact task coverage, validates every five-case cluster, regenerates
every compact review row, checks session splits, and verifies all artifact
hashes.

## Completion Boundary

Generation is complete when the versioned summary and independent validation
record agree on the source, eligibility, dataset, and review-packet hashes.
Evaluation eligibility additionally requires the stratified expert-QC audit,
score-blind protocol registration, and a held-out case manifest that binds
those artifacts. The manifest, rather than fictitious row-level human review,
assigns runnable case status. Model inference remains unavailable until final
run configurations bind that manifest to a clean code commit.
