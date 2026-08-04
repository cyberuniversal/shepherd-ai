# MultiUAV Intervention Pilot Review Protocol

## Scope

This protocol implements the compact independent label-review step required by
the source code plan. It applies only to the 30-cluster, 150-case training
pilot. It does not approve the full dataset or authorize model inference.

The frozen blank packet is
`reports/multiuav_intervention_pilot_review_v2.csv`. Do not edit or overwrite
that file. Git and the generation summary bind its hash to the unreviewed
pilot. The superseded version 1 packet is retained only as diagnostic history.

## Reviewer Identity

The project team must arrange an independent reviewer and assign that person a
real pseudonymous identifier. Code can check the identifier's presence and
format but cannot prove the person's existence or independence. Do not use a
placeholder unless it is the registered pseudonym of the real reviewer.
Identifiers may contain 1-64 ASCII letters, digits, periods, underscores, or
hyphens, and must begin with a letter or digit.

Create a separate working copy:

```powershell
python scripts/start_multiuav_intervention_review.py `
  --reviewer-id <REAL_PROJECT_PSEUDONYM> `
  --output reports/multiuav_intervention_pilot_review_working_v2.csv
```

The command refuses to overwrite the frozen template.

## Required Judgments

The reviewer inspects one case per row. `instruction` is the exact text under
review. `entity_summary`, `uav_status_summary`, and `intervention_summary` are
concise aids; they do not replace the exact instruction.

The reviewer edits only:

- `case_valid`: exactly `yes` or `no`;
- `review_status`: `approved`, `needs_revision`, or `excluded`;
- `exclusion_reason`; and
- `reviewer_notes`.

An approved row requires `case_valid=yes` and a blank exclusion reason. A
`needs_revision` row requires `case_valid=no` and reviewer notes. An excluded
row requires an exclusion reason. Any rejected or excluded case applies to its
complete five-case cluster during later dataset construction.

The frozen template intentionally has blank `reviewer_id`, `review_status`,
`case_valid`, `exclusion_reason`, and `reviewer_notes` fields. This is expected,
not missing automatic output.

## Validation

After all 150 rows are complete:

```powershell
python scripts/validate_multiuav_intervention_review.py `
  --review-packet reports/multiuav_intervention_pilot_review_working_v2.csv `
  --output datasets/multiuav_plat/intervention_pilot_review_validation_v2.json
```

Structural validation does not prove reviewer identity or independence. The
project team must retain that provenance separately.

### Normalizing reviewer-authored accept notes

When a returned packet contains a reviewer note beginning with `Accept:` on
every row but leaves the formal judgment columns blank, the project may derive
the equivalent formal values reproducibly:

```powershell
python scripts/normalize_multiuav_intervention_review.py `
  --input docs/source_material/multiuav_intervention_pilot_review_response_2026-08-04.csv `
  --reviewer-id 1 `
  --output reports/multiuav_intervention_pilot_review_completed_v2.csv
```

The command sets only `reviewer_id`, `review_status=approved`,
`case_valid=yes`, and a blank `exclusion_reason`. It preserves every reviewer
note and immutable case field, rejects non-`Accept:` notes, refuses to replace
existing formal judgments, validates the completed packet before writing, and
does not overwrite the source response. This normalization records the
project's interpretation of existing notes; it does not establish reviewer
identity or independence.

## Revision And Exclusion

Do not repair generated text directly in the review CSV. Change the generation
template, add a regression test, generate a new versioned pilot, and re-review
affected cases. Exclusions remain cluster-level. A disputed judgment requires
a distinct real adjudicator and recorded rationale.

## Completion Boundary

Pilot review is complete only when all 150 rows pass structural validation,
reviewer identity and independence are attested, all revisions are regenerated
and re-reviewed, and cluster-level exclusions/adjudications are recorded. Until
then, no pilot case may enter model inference or publication summaries.

The active packet meets the structural boundary: project-supplied pseudonym
`1` identifies the user's PhD mentor, all 150 cases and 30 clusters are
approved, and no revision or exclusion was registered. The real identity is
held privately and is not committed. Code cannot verify human identity or
independence; the repository records the project owner's attestation and this
limit. `expert_qc_audit_v1.json` treats this review as stratified construction
quality control. It does not require or claim review of all 7,365 generated
rows.
