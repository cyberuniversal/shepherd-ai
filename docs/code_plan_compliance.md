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
| CP-32 | Implement M1-M4 and disclose any call-count confound. | partial | Versioned prompts and the provider-independent runner implement M1/M2 at one call and M3/M4 at two calls. M1/M2/M4 have byte-equivalent first-call prompts; M3 always uses its second call. Matching remains explicitly limited to model-call count. A local Qwen backend and revised-study inference are not implemented. |
| CP-33 | Enforce strict decisions and non-empty executable plans; retain `PARSE_ERROR`. | implemented | `src/shepherd_ai/multiuav_plan_contract.py` strictly parses the three decisions, enforces decision-specific question/plan invariants, rejects empty executable plans and malformed structures, and preserves raw failures as `PARSE_ERROR`. `src/shepherd_ai/multiuav_runner.py` applies the parser to every final call and retains raw output. |
| CP-34 | Recursively ground API values and record containment stage. | implemented | `src/shepherd_ai/multiuav_grounding_validator.py` freezes 11 endpoint schemas, recursively validates waypoint leaves, grounds values against parameter-compatible AGENT-visible evidence, records per-leaf provenance, enforces static bounds, and records first containment stage. M2-M4 invoke it through the method runner. No revised-study containment outcome has been evaluated. |
| CP-35 | Resolve both Qwen checkpoints to immutable 40-character commits. | implemented | `src/shepherd_ai/multiuav_model_revisions.py` pins 3B at `aa8e72537993ba99e69dfaafa59ed015b17504d1` and 7B at `a09a35458c702b33eeacc393d103063234e8bc28`. Both immutable revision endpoints were remotely verified in `datasets/multiuav_plat/model_revision_audit_v1.json`; no weights were downloaded or invoked. |
| CP-36 | Separate one deterministic accuracy run from three resource repetitions on 30 clusters. | not implemented | Sampling and run harness are not implemented. |
| CP-37 | Record the full safety, utility, fidelity, latency, token, memory, call, and GPU-energy trade-off. | not implemented | Metrics are registered; no revised-study run exists. |
| CP-38 | Use source-cluster bootstrap, paired differences, confidence intervals, and preregistered outcomes. | not implemented | Statistical unit is specified; primary outcomes and analysis code are not frozen. |
| CP-39 | Checkpoint every row with compatible resume and complete raw packages. | partial | Config-bound JSONL writes, per-row `fsync`, duplicate/config-drift rejection, zero-call resume, matrix completeness, and deterministic compact ZIP checkpoints are implemented. The final publication package with summaries, figures, failure examples, dependency versions, and complete runtime metadata does not exist. |
| CP-40 | Add corruption, conflict, empty-value, partial-cluster, revision, and smoke-leak regression gates. | partial | Alias corruption, trained-parser substitution, global-evidence leakage, generic resource-conflict, partial-cluster, privileged-field, deterministic reconstruction, review-packet mutation, empty-plan, blank-reference, strict-JSON, endpoint-schema, recursive-grounding, static-bound, and mutable-model-revision gates exist. Publication smoke-leak gates remain unimplemented. |

## Locked Protocol

| ID | Locked item | Status |
|---|---|---|
| LP-42 | 75 sessions and 1,500 authentic source tasks. | implemented and audited |
| LP-43 | 7,500 five-variant cases before exclusions. | partial; 150 unreviewed training-pilot cases exist, while the post-exclusion full upper bound remains 7,365 |
| LP-44 | Session-level 60/20/20 split. | implemented before task-level leakage exclusions |
| LP-45 | Primary stage-wise versus monolithic contrast; compute-matched confirmation preferred. | partial; call budgets and runner paths are frozen and M3/M4 are model-call-count matched, but no revised-study experiment exists |
| LP-46 | One deterministic accuracy run per immutable checkpoint. | not implemented |
| LP-47 | Thirty clusters, five variants, three resource repetitions. | partial; the 30-cluster pilot exists for construction review, but no model/resource run exists |
| LP-48 | Cached local-only weights and blocked non-loopback sockets. | not implemented for revised study |
| LP-49 | Board-energy counter or 20 Hz power integration. | not implemented |
| LP-50 | Static fidelity unless official-server execution occurs. | partial; scope decision remains unresolved |
| LP-51 | Text-first primary study; speech separately evaluated. | implemented as study scope |

## Definition Of Done

| ID | Completion requirement | Status |
|---|---|---|
| DoD-53 | Record every data and model checksum. | partial; source/data artifacts and immutable Qwen repository revisions are recorded, but weight-file checksums do not exist because weights are not cached |
| DoD-54 | No hidden reference field enters a prompt. | partial; prompt construction accepts only validated AGENT context and the frozen action/observation catalogs and has source-hashed leakage tests, but no revised-study model run exists |
| DoD-55 | Retain every expected method-case row, including failures and parse errors. | partial; the runner/checkpoint contract preserves raw parse failures and enforces complete matrices in synthetic tests, but no locked result matrix exists |
| DoD-56 | Verifiably connect the trained component end to end. | implemented for historical Shepherd DistilBERT wiring; revised M1-M4 models are not implemented |
| DoD-57 | Freeze protocol before inspecting final method scores. | partial; protocol exists but unresolved decisions prevent freezing |
| DoD-58 | Label smoke results and exclude them from figures. | partial; current smoke is labelled, publication-summary exclusion test remains absent |
| DoD-59 | Analyze accuracy and hardware repetitions at the correct unit. | not evaluated |
| DoD-60 | Report controlled-derivative, within-Qwen, static-fidelity, process-isolation, and call-budget limitations. | partial; protocol records them, final paper does not exist |
| DoD-61 | Derive conclusions from observed results. | not evaluated; no locked results exist |

## Immediate Gate

Human review under CP-29/CP-31 remains pending, but independent correctness
work may continue. The call budget, prompts, provider-independent runner,
strict parsers, recursive grounding validator, immutable Qwen revisions, and
checkpoint/resume contract are now frozen. The next non-review-dependent gate
is the local Qwen backend and offline-runtime isolation required by LP-48,
without using the unreviewed pilot. Model inference on study cases remains
blocked.
