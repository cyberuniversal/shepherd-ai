# Intervention Pilot Feedback Resolution

## Provenance

Received feedback is preserved verbatim at
`docs/source_material/multiuav_intervention_pilot_feedback_2026-07-31.txt`
(SHA-256 `3ceaa3689182e0497faf9a576f43883133fc81b094ffaf3aff44ab6dfb858a6e`).
The message contains protocol feedback, not row-level labels. Reviewer identity
and independence were not stated, so it is not counted as the required human
review.

## Disposition

| Feedback | Disposition | Resolution |
|---|---|---|
| Make the CSV compact. | accepted | Version 2 has 150 per-case rows. Each row contains one exact instruction and short entity, UAV-status, and intervention summaries. |
| Replace the repeated resource-conflict sentence. | accepted | The packet now reports the applied task-specific fleet mutation and base/case fleet state. The validator recomputes and verifies each conflict. |
| Spot-check generated columns. | accepted | Generation is followed by row-count, schema, uniqueness, label-balance, split, blank-review-field, artifact-hash, and negative-control checks. |
| Insert incorrect cases to prove rejection. | accepted with isolation | Two known-bad synthetic probes are stored separately. They are not inserted into pilot or evaluation data. |
| Add calibration and test cases to the pilot. | declined | The frozen protocol reserves those splits for later evaluation. Inspecting them during template debugging would create leakage. |
| Improve missing-fact coverage. | accepted within supported templates | Version 2 contains 15 explicit-UAV-identity and 15 coverage-threshold clusters, one of each in every scenario/difficulty stratum. No unsupported intervention type was invented. |
| Blank reviewer fields are acceptable. | confirmed | The protocol now states this explicitly for whoever performs the later manual review. |

## Remaining Boundary

Version 2 is structurally validated but still unreviewed. Its proposed labels
are not approved, gold, final, or evaluation data. Calibration and test remain
untouched by template debugging.
