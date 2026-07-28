# Code Plan Compliance

## Scope

This matrix tracks the complete implementation instructions and definition of
done in `docs/source_material/code_plan_2026-07-25.docx`. The source plan is
authoritative for the revised MultiUAV validation-placement study. Status terms
are limited to `implemented`, `partial`, `not implemented`, and `not
evaluated`.

The plan's feedback, bounded novelty, prohibited claims, locked protocol, and
venue positioning are reflected in
`docs/multiuav_validation_study_protocol.md`. They are not implementation
results.

## Build Order

| ID | Code-plan requirement | Status | Repository evidence or blocker |
|---|---|---|---|
| CP-25 | Pass correctness and smoke gates before the full GPU run. | partial | Source, split, eligibility, alias, wiring, and unit-test gates exist. Revised-study model inference remains blocked. |
| CP-26 | Use a clean research branch, preserve old work, and record final-run commits. | implemented | Active branch is `codex/multiuav-validation-study`; historical notebooks and results remain versioned. No final run exists yet. |
| CP-27 | Remove hard-coded mistranscriptions/test aliases; wire trained DistilBERT; fail on parser substitution. | implemented | Aliases were removed from `src/shepherd_ai/intent.py`; `HfTokenClassifierSpanPredictor` is wired into the historical integrated path; `tests/test_integrated_prototype.py` patches the deterministic parser to fail; the hashed smoke artifact is retained. DistilBERT remains excluded from M1-M4. |
| CP-28 | Pin and verify MultiUAV-Plat commit, archive hash, 75 sessions, and 1,500 tasks. | implemented | `docs/multiuav_source_acquisition.md` and `datasets/multiuav_plat/source_audit_v1.json`. |
| CP-29 | Build five linked variants per task without exposing hidden references. | partial | A deterministic training-only pilot contains 30 complete clusters and 150 template-generated cases. It is bound to the pinned source and eligibility manifest and passes source reconstruction, privileged-field, cluster-completeness, and review-packet validation. All 30 clusters remain pending human review; the full 1,473-cluster dataset is not generated. |
| CP-30 | Split by session; keep clusters together; report overlap. | implemented | `docs/multiuav_split_protocol.md`, `datasets/multiuav_plat/session_split_v1.json`, and task-level leakage exclusions. The plan's 4,500/1,500/1,500 counts are pre-exclusion targets; prospective retained counts are separately reported. |
| CP-31 | Produce a compact review packet and use real reviewer identities. | partial | `reports/multiuav_intervention_pilot_review_v1.csv` contains one row per pilot cluster and blank reviewer fields. Separate-copy creation and completed-packet validation are implemented under `docs/multiuav_intervention_review_protocol.md`. No identity was fabricated. Reviewer registration, review, and any needed adjudication are not completed. |
| CP-32 | Implement M1-M4 and disclose any call-count confound. | not implemented | M1-M4 are specified only. M3 call semantics and the exactly matched M4 budget remain unresolved. |
| CP-33 | Enforce strict decisions and non-empty executable plans; retain `PARSE_ERROR`. | not implemented | Output contract is documented but no revised-study parser exists. |
| CP-34 | Recursively ground API values and record containment stage. | not implemented | Validator scope is documented but not coded. |
| CP-35 | Resolve both Qwen checkpoints to immutable 40-character commits. | not implemented | Model family is selected; immutable revisions have not been resolved or frozen. |
| CP-36 | Separate one deterministic accuracy run from three resource repetitions on 30 clusters. | not implemented | Sampling and run harness are not implemented. |
| CP-37 | Record the full safety, utility, fidelity, latency, token, memory, call, and GPU-energy trade-off. | not implemented | Metrics are registered; no revised-study run exists. |
| CP-38 | Use source-cluster bootstrap, paired differences, confidence intervals, and preregistered outcomes. | not implemented | Statistical unit is specified; primary outcomes and analysis code are not frozen. |
| CP-39 | Checkpoint every row with compatible resume and complete raw packages. | not implemented | Revised-study runner and checkpoint/resume format do not exist. |
| CP-40 | Add corruption, conflict, empty-value, partial-cluster, revision, and smoke-leak regression gates. | partial | Alias corruption, trained-parser substitution, global-evidence leakage, generic resource-conflict, partial-cluster, privileged-field, deterministic reconstruction, and review-packet mutation gates exist. Empty-plan/value, mutable-model-revision, and publication smoke-leak gates remain unimplemented. |

## Locked Protocol

| ID | Locked item | Status |
|---|---|---|
| LP-42 | 75 sessions and 1,500 authentic source tasks. | implemented and audited |
| LP-43 | 7,500 five-variant cases before exclusions. | partial; 150 unreviewed training-pilot cases exist, while the post-exclusion full upper bound remains 7,365 |
| LP-44 | Session-level 60/20/20 split. | implemented before task-level leakage exclusions |
| LP-45 | Primary stage-wise versus monolithic contrast; compute-matched confirmation preferred. | partial; registered but call budgets are unresolved |
| LP-46 | One deterministic accuracy run per immutable checkpoint. | not implemented |
| LP-47 | Thirty clusters, five variants, three resource repetitions. | partial; the 30-cluster pilot exists for construction review, but no model/resource run exists |
| LP-48 | Cached local-only weights and blocked non-loopback sockets. | not implemented for revised study |
| LP-49 | Board-energy counter or 20 Hz power integration. | not implemented |
| LP-50 | Static fidelity unless official-server execution occurs. | partial; scope decision remains unresolved |
| LP-51 | Text-first primary study; speech separately evaluated. | implemented as study scope |

## Definition Of Done

| ID | Completion requirement | Status |
|---|---|---|
| DoD-53 | Record every data and model checksum. | partial; source/data artifacts are hashed, Qwen revisions are absent |
| DoD-54 | No hidden reference field enters a prompt. | partial; pilot records pass recursive privileged-field checks and case-context materialization tests, but no revised-study prompt runner exists |
| DoD-55 | Retain every expected method-case row, including failures and parse errors. | not implemented |
| DoD-56 | Verifiably connect the trained component end to end. | implemented for historical Shepherd DistilBERT wiring; revised M1-M4 models are not implemented |
| DoD-57 | Freeze protocol before inspecting final method scores. | partial; protocol exists but unresolved decisions prevent freezing |
| DoD-58 | Label smoke results and exclude them from figures. | partial; current smoke is labelled, publication-summary exclusion test remains absent |
| DoD-59 | Analyze accuracy and hardware repetitions at the correct unit. | not evaluated |
| DoD-60 | Report controlled-derivative, within-Qwen, static-fidelity, process-isolation, and call-budget limitations. | partial; protocol records them, final paper does not exist |
| DoD-61 | Derive conclusions from observed results. | not evaluated; no locked results exist |

## Immediate Gate

The next code-plan task remains CP-29/CP-31 human review. The 30-cluster
training pilot has been generated and deterministically validated, but all
labels and rewrites remain unreviewed. The review/adjudication procedure must
be frozen and the pilot reviewed before templates are revised or the full
1,473-cluster intervention dataset is generated. Model inference remains
blocked.
