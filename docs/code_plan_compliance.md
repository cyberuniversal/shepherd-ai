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
| CP-25 | Pass correctness and smoke gates before the full GPU run. | implemented for pre-inference accuracy gates; one excluded feasibility attempt preserved | Source, split, eligibility, alias, wiring, model-cache, synthetic-load, scoring, unit-test, and cache/runtime preflight gates pass. A one-row local 3B attempt was aborted after a 389.9-second call, preserved with hashes, and excluded. Final configs require rebinding before cluster execution. |
| CP-26 | Use a clean research branch, preserve old work, and record final-run commits. | implemented | Active branch is `codex/multiuav-validation-study`; historical notebooks and results remain versioned. No final run exists yet. |
| CP-27 | Remove hard-coded mistranscriptions/test aliases; wire trained DistilBERT; fail on parser substitution. | implemented | Aliases were removed from `src/shepherd_ai/intent.py`; `HfTokenClassifierSpanPredictor` is wired into the historical integrated path; `tests/test_integrated_prototype.py` patches the deterministic parser to fail; the hashed smoke artifact is retained. DistilBERT remains excluded from M1-M4. |
| CP-28 | Pin and verify MultiUAV-Plat commit, archive hash, 75 sessions, and 1,500 tasks. | implemented | `docs/multiuav_source_acquisition.md` and `datasets/multiuav_plat/source_audit_v1.json`. |
| CP-29 | Build five linked variants per task without exposing hidden references. | implemented as controlled-derivative construction | The corrected 30-cluster pilot is structurally approved. `intervention_dataset_v1.json` applies its construction to all 1,473 eligible source tasks, yielding 7,365 cases after 27 recorded cross-split duplicate exclusions. Exact source reconstruction, privileged-field, cluster-completeness, task-specific resource-conflict, review-packet, split, and hash gates pass. Full labels are deterministic controlled derivatives, not claimed human-authored judgments. |
| CP-30 | Split by session; keep clusters together; report overlap. | implemented | `docs/multiuav_split_protocol.md`, `datasets/multiuav_plat/session_split_v1.json`, and task-level leakage exclusions. The plan's 4,500/1,500/1,500 counts are pre-exclusion targets; prospective retained counts are separately reported. |
| CP-31 | Produce a compact review packet and use real reviewer identities. | implemented as sampled expert QC | `reports/multiuav_intervention_pilot_review_completed_v2.csv` contains 150 approved pilot rows under pseudonym `1`, identified by the project owner as a PhD mentor. `expert_qc_audit_v1.json` binds this balanced 30-cluster review to byte-equivalent full-dataset clusters and explicitly states that full row-level review was neither required nor performed. The real identity remains private; independence is project-attested and not machine-verifiable. |
| CP-32 | Implement M1-M4 and disclose any call-count confound. | partial | Versioned prompts and the provider-independent runner implement M1/M2 at one call and M3/M4 at two calls. M1/M2/M4 have byte-equivalent first-call prompts; M3 always uses its second call. Matching remains explicitly limited to model-call count. One approved M1 row ran in an excluded local feasibility attempt; no complete M1-M4 matrix has run. |
| CP-33 | Enforce strict decisions and non-empty executable plans; retain `PARSE_ERROR`. | implemented | `src/shepherd_ai/multiuav_plan_contract.py` strictly parses the three decisions, enforces decision-specific question/plan invariants, rejects empty executable plans and malformed structures, and preserves raw failures as `PARSE_ERROR`. `src/shepherd_ai/multiuav_runner.py` applies the parser to every final call and retains raw output. |
| CP-34 | Recursively ground API values and record containment stage. | implemented | `src/shepherd_ai/multiuav_grounding_validator.py` freezes 11 endpoint schemas, recursively validates waypoint leaves, grounds values against parameter-compatible AGENT-visible evidence, records per-leaf provenance, enforces static bounds, and records first containment stage. M2-M4 invoke it through the method runner. No revised-study containment outcome has been evaluated. |
| CP-35 | Resolve both Qwen checkpoints to immutable 40-character commits. | implemented | `src/shepherd_ai/multiuav_model_revisions.py` pins 3B at `aa8e72537993ba99e69dfaafa59ed015b17504d1` and 7B at `a09a35458c702b33eeacc393d103063234e8bc28`. Both revision endpoints were remotely verified, cached, checksummed, and synthetically invoked in separate later artifacts. |
| CP-36 | Separate one deterministic accuracy run from three resource repetitions on 30 clusters. | partial | `accuracy_case_manifest_v1.json` approves 284 held-out clusters and 1,420 cases for one deterministic accuracy run per model. Final configs bind one 5,680-row accuracy matrix per model to commit `456b864d6b0dd9dce5da5a5fdcb497bfc0510a37`; both preflights pass without resource monitoring. Resource configs remain separate: `resource_schedule_candidate_v1.json` selects 30 tasks and registers 24 model-method-repetition conditions; warm-up and final hardware bindings remain resource-only blockers. |
| CP-37 | Record the full safety, utility, fidelity, latency, token, memory, call, and GPU-energy trade-off. | partial | The frozen scorer records raw and post-gate unsafe proceed, decision utility, schema/endpoint/parameter/official-command fidelity, parse/backend failures, and containment. Method-case telemetry records wall time, calls, tokens, process RAM, board/process VRAM, raw NVML samples, and GPU-board energy. No revised-study measurement exists. |
| CP-38 | Use source-cluster bootstrap, paired differences, confidence intervals, and preregistered outcomes. | implemented as score-blind protocol; not evaluated | `accuracy_protocol_freeze_v1.json` registers M3-minus-M1 primary and M3-minus-M4 confirmatory contrasts, two directed primary outcomes, post-gate system semantics, retained parse/backend failures, 10,000 fixed-seed cluster bootstrap draws, 95% percentile intervals, no null-hypothesis tests, and exploratory secondary outcomes. `scoring_contract_audit_v1.json` binds deterministic label-separated scoring without reading study rows. No study row has been analyzed. |
| CP-39 | Checkpoint every row with compatible resume and complete raw packages. | partial | Schema-v3 config-bound JSONL writes, per-row `fsync`, duplicate/config-drift rejection, zero-call resume, durable progress callbacks, matrix completeness, per-row resource reports, and deterministic compact ZIP checkpoints are implemented and exposed through the accuracy CLI. The final publication package does not exist. |
| CP-40 | Add corruption, conflict, empty-value, partial-cluster, revision, and smoke-leak regression gates. | implemented as pre-run contracts | Alias corruption, trained-parser substitution, global-evidence leakage, task-specific resource-conflict, partial-cluster, privileged-field, deterministic reconstruction, review-packet mutation, empty-plan, blank-reference, strict-JSON, endpoint-schema, recursive-grounding, static-bound, mutable-model-revision, and publication smoke-leak gates exist. The publication gate rejects synthetic/resource/unapproved/incomplete accuracy matrices while retaining parse failures. Two stored negative controls remain synthetic contract evidence only. |

## Locked Protocol

| ID | Locked item | Status |
|---|---|---|
| LP-42 | 75 sessions and 1,500 authentic source tasks. | implemented and audited |
| LP-43 | 7,500 five-variant cases before exclusions. | implemented as dataset construction; 1,500 source tasks imply 7,500 pre-exclusion cases, and 27 recorded source exclusions yield 7,365 unreviewed draft cases |
| LP-44 | Session-level 60/20/20 split. | implemented before task-level leakage exclusions |
| LP-45 | Primary stage-wise versus monolithic contrast; compute-matched confirmation preferred. | implemented as preregistration; M3-minus-M1 is primary and M3-minus-M4 confirmatory, with no revised-study result yet |
| LP-46 | One deterministic accuracy run per immutable checkpoint. | partial; the builder and runner enforce one deterministic commit-bound config per pinned checkpoint, but neither locked matrix has run |
| LP-47 | Thirty clusters, five variants, three resource repetitions. | partial; a separate 30-task held-out resource candidate and 24 condition orders are source-hashed, but approved five-case clusters and model/resource runs do not exist |
| LP-48 | Cached local-only weights and blocked non-loopback sockets. | partial; both pinned snapshots are cached outside Git with complete checksums and successful synthetic load/generation smokes. The 3B failed remote-lookup attempt and earlier 32-token success are preserved. The 7B smoke used explicit CPU/disk offload. No external firewall control is registered. |
| LP-49 | Board-energy counter or 20 Hz power integration. | partial; NVML counter-first measurement and 20 Hz trapezoidal fallback are implemented and synthetically probed, but thermal controls and study repetitions remain absent |
| LP-50 | Static fidelity unless official-server execution occurs. | implemented; `execution_scope_audit_v1.json` freezes static API, parameter, and official-command fidelity and prohibits live mission-success claims |
| LP-51 | Text-first primary study; speech separately evaluated. | implemented as study scope |

## Definition Of Done

| ID | Completion requirement | Status |
|---|---|---|
| DoD-53 | Record every data and model checksum. | partial; source/data artifacts, both immutable Qwen revisions, and every cached 3B and 7B snapshot file are recorded. Final run artifacts do not yet exist. |
| DoD-54 | No hidden reference field enters a prompt. | partial; prompt construction accepts only validated AGENT context and the frozen action/observation catalogs and has source-hashed leakage tests, but no revised-study model run exists |
| DoD-55 | Retain every expected method-case row, including failures and parse errors. | partial; the runner/checkpoint contract preserves raw parse failures and enforces complete matrices in synthetic tests, but no locked result matrix exists |
| DoD-56 | Verifiably connect the trained component end to end. | implemented for historical Shepherd DistilBERT wiring; revised M1-M4 models are not implemented |
| DoD-57 | Freeze protocol before inspecting final method scores. | partial after disclosed deviation; protocol, scorer, manifest, and model config were bound before the excluded attempt, and no aggregate, comparative, or hidden-label score was inspected, but one raw output and parse status were viewed during feasibility diagnosis |
| DoD-58 | Label smoke results and exclude them from figures. | partial; current smokes are labelled and the tested publication-admission gate rejects synthetic and resource rows, but no final figure pipeline exists |
| DoD-59 | Analyze accuracy and hardware repetitions at the correct unit. | not evaluated |
| DoD-60 | Report controlled-derivative, within-Qwen, static-fidelity, process-isolation, and call-budget limitations. | partial; protocol records them, final paper does not exist |
| DoD-61 | Derive conclusions from observed results. | not evaluated; no locked results exist |

## Immediate Gate

Structural review of the corrected version 2 pilot, deterministic full-dataset
generation, sampled expert-QC audit, score-blind protocol registration, the
1,420-case held-out approval manifest, and deterministic label-separated
scoring contract pass. The 3B and 7B cache
preflights and synthetic load/generation smokes now pass with complete file
checksums and no study-case use. Static fidelity is frozen, and method-case
NVML instrumentation has a source-hashed synthetic probe. A deterministic
30-task held-out candidate subset and all 24 model-method-repetition condition
orders are recorded without model invocation. Final accuracy configs are bound
to the frozen execution commit, and both complete snapshot/runtime preflights
pass. The readiness audit reports no accuracy blocker. Warm-up and thermal
controls remain separate blockers for the later resource experiment. No study
inference has started.
