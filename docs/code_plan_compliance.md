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
| CP-25 | Pass correctness and smoke gates before the full GPU run. | implemented for attempt 3 | Source, split, eligibility, alias, wiring, model-cache, synthetic-load, scoring-contract, unit-test, and cache/runtime gates pass. Resource preflight v3 independently admitted both frozen models against the cooldown-aware attempt-3 execution revision on one RTX 3090 without loading either model or starting measurement. Its summaries, logs, Kubernetes state, and validation metadata are preserved. |
| CP-26 | Use a clean research branch, preserve old work, and record final-run commits. | implemented | Active branch is `codex/multiuav-validation-study`; historical notebooks and negative results remain versioned. The complete 3B and 7B checkpoint artifacts record the bound execution commit, model revisions, config hashes, and result hashes. |
| CP-27 | Remove hard-coded mistranscriptions/test aliases; wire trained DistilBERT; fail on parser substitution. | implemented | Aliases were removed from `src/shepherd_ai/intent.py`; `HfTokenClassifierSpanPredictor` is wired into the historical integrated path; `tests/test_integrated_prototype.py` patches the deterministic parser to fail; the hashed smoke artifact is retained. DistilBERT remains excluded from M1-M4. |
| CP-28 | Pin and verify MultiUAV-Plat commit, archive hash, 75 sessions, and 1,500 tasks. | implemented | `docs/multiuav_source_acquisition.md` and `datasets/multiuav_plat/source_audit_v1.json`. |
| CP-29 | Build five linked variants per task without exposing hidden references. | implemented as controlled-derivative construction | The corrected 30-cluster pilot is structurally approved. `intervention_dataset_v1.json` applies its construction to all 1,473 eligible source tasks, yielding 7,365 cases after 27 recorded cross-split duplicate exclusions. Exact source reconstruction, privileged-field, cluster-completeness, task-specific resource-conflict, review-packet, split, and hash gates pass. Full labels are deterministic controlled derivatives, not claimed human-authored judgments. |
| CP-30 | Split by session; keep clusters together; report overlap. | implemented | `docs/multiuav_split_protocol.md`, `datasets/multiuav_plat/session_split_v1.json`, and task-level leakage exclusions. The plan's 4,500/1,500/1,500 counts are pre-exclusion targets; prospective retained counts are separately reported. |
| CP-31 | Produce a compact review packet and use real reviewer identities. | implemented as sampled expert QC | `reports/multiuav_intervention_pilot_review_completed_v2.csv` contains 150 approved pilot rows under pseudonym `1`, identified by the project owner as a PhD mentor. `expert_qc_audit_v1.json` binds this balanced 30-cluster review to byte-equivalent full-dataset clusters and explicitly states that full row-level review was neither required nor performed. The real identity remains private; independence is project-attested and not machine-verifiable. |
| CP-32 | Implement M1-M4 and disclose any call-count confound. | implemented | Versioned prompts and the provider-independent runner implement M1/M2 at one call and M3/M4 at two calls. M1/M2/M4 have byte-equivalent first-call prompts; M3 always uses its second call. Matching remains explicitly limited to model-call count. Complete M1-M4 matrices exist for both frozen models, but no method outcome has been scored. |
| CP-33 | Enforce strict decisions and non-empty executable plans; retain `PARSE_ERROR`. | implemented | `src/shepherd_ai/multiuav_plan_contract.py` strictly parses the three decisions, enforces decision-specific question/plan invariants, rejects empty executable plans and malformed structures, and preserves raw failures as `PARSE_ERROR`. `src/shepherd_ai/multiuav_runner.py` applies the parser to every final call and retains raw output. |
| CP-34 | Recursively ground API values and record containment stage. | implemented | `src/shepherd_ai/multiuav_grounding_validator.py` freezes 11 endpoint schemas, recursively validates waypoint leaves, grounds values against parameter-compatible AGENT-visible evidence, records per-leaf provenance, enforces static bounds, and records first containment stage. M2-M4 invoke it through the method runner. Descriptive containment outcomes are preserved in the scored-row archives; clustered comparison is pending. |
| CP-35 | Resolve both Qwen checkpoints to immutable 40-character commits. | implemented | `src/shepherd_ai/multiuav_model_revisions.py` pins 3B at `aa8e72537993ba99e69dfaafa59ed015b17504d1` and 7B at `a09a35458c702b33eeacc393d103063234e8bc28`. Both revision endpoints were remotely verified, cached, checksummed, and synthetically invoked in separate later artifacts. |
| CP-36 | Separate one deterministic accuracy run from three resource repetitions on 30 clusters. | implemented | `accuracy_case_manifest_v1.json` approves 284 held-out clusters and 1,420 cases. One 5,680-row accuracy matrix per frozen model is admitted. `resource_schedule_v1.json` binds 30 approved clusters, 150 cases, and 24 conditions to the frozen RTX 3090 protocol. Attempts 1 and 2 are preserved failures. Attempt 3 completed all 24 conditions and 3,600 rows; admission and registered separate-repetition analysis pass. |
| CP-37 | Record the full safety, utility, fidelity, latency, token, memory, call, and GPU-energy trade-off. | implemented | Accuracy scoring records raw and post-gate unsafe proceed, decision utility, schema/endpoint/parameter/official-command fidelity, parse/backend failures, and containment for all 11,360 rows. The separate 3,600-row resource campaign now provides registered duration, token, model-call, RAM, VRAM, and GPU-board-energy summaries for all models, methods, and repetitions. Resource outcomes remain secondary and exploratory. |
| CP-38 | Use source-cluster bootstrap, paired differences, confidence intervals, and preregistered outcomes. | implemented | `accuracy_protocol_freeze_v1.json` registers M3-minus-M1 primary and M3-minus-M4 confirmatory contrasts, two directed primary outcomes, post-gate system semantics, retained failures, 10,000 fixed-seed cluster-bootstrap draws, 95% percentile intervals, and no null-hypothesis tests. All eight registered model-contrast-outcome analyses are complete with deterministic evidence archives and a bounded report. |
| CP-39 | Checkpoint every row with compatible resume and complete raw packages. | implemented | Schema-v3 config-bound JSONL writes, per-row `fsync`, duplicate/config-drift rejection, zero-call resume, durable progress callbacks, matrix completeness, and deterministic compact ZIP checkpoints are implemented. The preserved 3B and 7B accuracy archives each contain all 5,680 expected rows and pass admission. Resource attempts 1 and 2 retain their failed packages. Attempt 3 retains all 3,600 rows, 24 valid checkpoint ZIPs, 24 start controls, condition logs and summaries, Kubernetes evidence, and a 170-file source-hash manifest in one verified complete archive; every condition and checkpoint passed score-blind admission. |
| CP-40 | Add corruption, conflict, empty-value, partial-cluster, revision, and smoke-leak regression gates. | implemented as pre-run contracts | Alias corruption, trained-parser substitution, global-evidence leakage, task-specific resource-conflict, partial-cluster, privileged-field, deterministic reconstruction, review-packet mutation, empty-plan, blank-reference, strict-JSON, endpoint-schema, recursive-grounding, static-bound, mutable-model-revision, and publication smoke-leak gates exist. The publication gate rejects synthetic/resource/unapproved/incomplete accuracy matrices while retaining parse failures. Two stored negative controls remain synthetic contract evidence only. |

## Locked Protocol

| ID | Locked item | Status |
|---|---|---|
| LP-42 | 75 sessions and 1,500 authentic source tasks. | implemented and audited |
| LP-43 | 7,500 five-variant cases before exclusions. | implemented as dataset construction; 1,500 source tasks imply 7,500 pre-exclusion cases, and 27 recorded source exclusions yield 7,365 unreviewed draft cases |
| LP-44 | Session-level 60/20/20 split. | implemented before task-level leakage exclusions |
| LP-45 | Primary stage-wise versus monolithic contrast; compute-matched confirmation preferred. | implemented as preregistration; M3-minus-M1 is primary and M3-minus-M4 confirmatory, with no revised-study result yet |
| LP-46 | One deterministic accuracy run per immutable checkpoint. | implemented; one complete admitted 5,680-row matrix exists for each pinned 3B and 7B checkpoint |
| LP-47 | Thirty clusters, five variants, three resource repetitions. | implemented; attempt 3 completed all 24 conditions and 3,600 rows, passed score-blind admission, and was analyzed with repetitions kept separate |
| LP-48 | Cached local-only weights and blocked non-loopback sockets. | partial; both pinned snapshots are cached outside Git with complete checksums and successful synthetic load/generation smokes. The 3B failed remote-lookup attempt and earlier 32-token success are preserved. The 7B smoke used explicit CPU/disk offload. No external firewall control is registered. |
| LP-49 | Board-energy counter or 20 Hz power integration. | implemented; every admitted attempt-3 condition passed the frozen NVML identity, telemetry, energy-counter/fallback, thermal, warm-up, and process-isolation controls |
| LP-50 | Static fidelity unless official-server execution occurs. | implemented; `execution_scope_audit_v1.json` freezes static API, parameter, and official-command fidelity and prohibits live mission-success claims |
| LP-51 | Text-first primary study; speech separately evaluated. | implemented as study scope |

## Definition Of Done

| ID | Completion requirement | Status |
|---|---|---|
| DoD-53 | Record every data and model checksum. | implemented for the completed study runs; source/data artifacts, immutable Qwen revisions, cached snapshot inventories, complete accuracy checkpoints, all 170 attempt-3 resource files, analysis outputs, tables, figures, and manifests are SHA-256 bound |
| DoD-54 | No hidden reference field enters a prompt. | implemented | Prompt construction accepts only validated AGENT context and the frozen action/observation catalogs; source-hashed leakage tests pass, complete matrices admit only approved evaluation rows, and hidden labels remained inaccessible through admission. |
| DoD-55 | Retain every expected method-case row, including failures and parse errors. | implemented | Both sealed accuracy archives retain all 11,360 expected method-case rows. Attempt 3 retains all 3,600 resource rows; attempts 1 and 2 remain preserved as negative infrastructure evidence. Admission gates reject missing, duplicate, unapproved, synthetic, or cross-run rows. |
| DoD-56 | Verifiably connect the trained component end to end. | implemented for historical Shepherd DistilBERT wiring; revised M1-M4 models are not implemented |
| DoD-57 | Freeze protocol before inspecting final method scores. | implemented with disclosed deviations | Accuracy protocol, scorer, manifests, model configs, complete matrices, and score-blind admission were frozen before scoring. Resource analysis was bound after execution and admission but before aggregate inspection to already registered source protocols; it is not called a preregistration. The excluded accuracy feasibility-row inspection and one admitted resource-row diagnostic inspection are preserved and disclosed. |
| DoD-58 | Label smoke results and exclude them from figures. | implemented | The publication figure loader accepts only the admitted scoring and registered bootstrap summaries, validates their binding and evidence archive, and records `smoke_rows_included: false`, `resource_rows_included: false`, and `raw_model_outputs_accessed: false` in the figure manifest. |
| DoD-59 | Analyze accuracy and hardware repetitions at the correct unit. | implemented; both analyses use source-task clusters, and resource repetitions are reported separately without pooling |
| DoD-60 | Report controlled-derivative, within-Qwen, static-fidelity, process-isolation, and call-budget limitations. | implemented in the accuracy/resource reports and integrated manuscript draft; final venue review remains pending |
| DoD-61 | Derive conclusions from observed results. | implemented in a working draft; the conclusion reports favorable 7B and negative 3B results plus model-dependent resource trade-offs, without a universal claim |

## Immediate Gate

Structural review of the corrected version 2 pilot, deterministic full-dataset
generation, sampled expert-QC audit, score-blind protocol registration, the
1,420-case held-out approval manifest, and deterministic label-separated
scoring contract pass. The 3B and 7B cache
preflights and synthetic load/generation smokes now pass with complete file
checksums and no study-case use. Static fidelity is frozen, and method-case
NVML instrumentation has a source-hashed synthetic probe. A deterministic final
30-task held-out subset, all 150 approved cases, all 24 conditions, and the
RTX 3090 measurement controls are recorded without resource-model invocation. Final accuracy configs
are bound to the frozen execution commit. The 3B and 7B runs produced two
complete 5,680-row sealed matrices, and `accuracy_matrix_admission_v1.json`
admits all 11,360 rows without pre-admission hidden-label access or scoring.
Registered label-separated deterministic scoring is now complete, with derived
rows separated from aggregate summaries. The registered source-cluster
bootstrap and accuracy figure generation are also complete, with exact source
tables and a provenance manifest. Resource preflight v2 passed, but campaign
attempt 2 stopped after one complete condition because the next condition's
idle baseline remained at 68 C against the frozen 60 C maximum. The partial
raw package is preserved and unscored. Baseline acquisition now waits for both
idle and thermal eligibility within the existing 600-second window, the focused
regressions and full suite pass, and all 24 attempt-3 configs are bound to the
resulting execution commit. No-inference RTX 3090 preflight v3 passed both
frozen-model checks on one GPU UUID, with zero model loading and measurement.
Attempt 3 then completed all 24 conditions and 3,600 rows on one locked RTX
3090 with zero pod restarts. Its full raw package and Kubernetes evidence are
hash-preserved without output or label inspection. The score-blind resource
admission gate subsequently verified all 170 archived files, frozen bindings,
checkpoints, exact condition matrices, telemetry, start controls, and hardware
identity without scoring or hidden-label access. The registered secondary
aggregate analysis is now complete with repetitions kept separate, 10,000
fixed-seed source-cluster bootstrap draws per paired analysis, deterministic
safe-derived and bootstrap-evidence archives, exact source tables, two figures,
and a provenance manifest. One post-admission raw-output inspection deviation
is preserved and disclosed. The integrated working manuscript passes a
25-check, 22-artifact internal traceability audit. Its 250-word abstract,
seven matched citation/reference identifiers, and four embedded registered
figures are machine-checked. A hash-bound external-review packet is ready but
has not been reviewed. The exact next gate is external scientific/manuscript
review, followed by venue selection, venue-specific formatting, and final
submission review.
