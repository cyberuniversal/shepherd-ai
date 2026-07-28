# MultiUAV Intervention Pilot Review Protocol

## Scope

This protocol implements the compact independent label-review step required by
paragraph 30 of `docs/source_material/code_plan_2026-07-25.docx`. It applies
only to the 30-cluster training pilot. It does not approve the full dataset or
authorize model inference.

The frozen blank packet remains:

`reports/multiuav_intervention_pilot_review_v1.csv`

Do not edit or overwrite that file. Git and the generation summary bind its
hash to the unreviewed pilot.

## Reviewer Identity

The project team must arrange an independent reviewer and assign that person a
real pseudonymous identifier. The identifier is provenance, not a generated
label. Code can check that it is present and consistently formatted, but cannot
prove that the person exists or is independent.

Do not use placeholders such as `reviewer_001` unless that is the registered
pseudonym of the real reviewer.

Create a separate working copy:

```powershell
python scripts/start_multiuav_intervention_review.py `
  --reviewer-id <REAL_PROJECT_PSEUDONYM> `
  --output reports/multiuav_intervention_pilot_review_working_v1.csv
```

The command refuses to overwrite the frozen template.

## Required Judgments

The reviewer inspects one cluster per row and edits only these fields:

- `canonical_valid`
- `alias_valid`
- `missing_valid`
- `restored_valid`
- `conflict_valid`
- `review_status`
- `exclusion_reason`
- `reviewer_notes`

Every validity field must be exactly `yes` or `no`.

Allowed review statuses:

- `approved`: all five validity fields are `yes`; exclusion reason is blank.
- `needs_revision`: at least one validity field is `no`; reviewer notes explain
  the required correction.
- `excluded`: the cluster must not be used; exclusion reason is required.

The canonical and alias text, generated controls, identifiers, strata,
automatic-validation result, and conflict summary are immutable review
evidence. The validator rejects edits to those fields.

## Validation

After all 30 rows are complete:

```powershell
python scripts/validate_multiuav_intervention_review.py `
  --review-packet reports/multiuav_intervention_pilot_review_working_v1.csv `
  --output datasets/multiuav_plat/intervention_pilot_review_validation_v1.json
```

Structural validation does not prove reviewer identity or independence. The
project team must retain that provenance separately.

## Revision And Exclusion

Do not repair generated text directly in the review CSV.

- For `needs_revision`, change the generation template in source code, add a
  regression test, generate a new versioned pilot, and review the affected
  version again.
- For `excluded`, remove the complete five-case cluster from later dataset
  construction. Partial clusters are invalid.
- If the project team disputes a review judgment, a distinct real adjudicator
  and rationale are required before changing the disposition. The current
  single-review packet does not implement or claim adjudication.

## Completion Boundary

Pilot review is complete only when:

1. all 30 rows pass structural validation;
2. reviewer identity and independence are attested by the project team;
3. every `needs_revision` row has been regenerated and re-reviewed;
4. exclusions are recorded at complete-cluster granularity; and
5. any disputed judgment has real adjudication provenance.

Until then, the pilot remains unreviewed or under review and cannot enter model
inference or publication summaries.
