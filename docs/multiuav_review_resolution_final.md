# MultiUAV Review Resolution

## Reviewed Material

The returned packet contains 150 accepted rows from 30 training-only clusters.
The exact reviewer response is preserved at
`docs/source_material/multiuav_intervention_pilot_review_response_2026-08-04.csv`.
The normalized structural record is
`reports/multiuav_intervention_pilot_review_completed_v2.csv`, with reviewer
pseudonym `1`, `review_status=approved`, `case_valid=yes`, and no exclusions.

## Resolution Ledger

| Comment | Count | Final resolution |
|---|---:|---|
| Accept case | 150 | Recorded as approved in the normalized packet. |
| Prefer “assign” to “assigned” | 8 | Accepted wording note. Frozen evaluated text is preserved. |
| Duplicated “Drone” token | 27 | Accepted source-text defect. Frozen evaluated text is preserved. |
| “Random coordinates” wording conflicts with fixed coordinates | 1 | Accepted wording note. Frozen evaluated text is preserved. |

The compact packet, task-specific resource conflicts, negative validator
controls, and balanced fact-type coverage requested in the earlier feedback
were implemented before the final review. The suggestion to review examples
from calibration or test was intentionally not followed: the pilot remained
training-only to avoid exposing held-out evaluation content.

## Research-Integrity Decision

No accepted wording defect is silently rewritten after model inference. Such a
rewrite would produce cases that no longer match the preserved checkpoints and
reported hashes. The defects are therefore disclosed as source/derivative text
limitations, while the accepted labels remain unchanged. This ledger addresses
the comments without retroactively modifying the frozen experiment.
