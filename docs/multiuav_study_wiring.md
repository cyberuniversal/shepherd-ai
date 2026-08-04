# MultiUAV Validation Study Wiring

## Active Path

The primary revised experiment is text-first:

```text
frozen MultiUAV source task
  -> validated controlled derivative under stratified expert QC
  -> method M1, M2, M3, or M4
  -> strict API-plan parser
  -> deterministic evidence, provenance, and safety validation
  -> frozen static plan-fidelity scoring
  -> label-separated scoring and resource measurement
```

The source, split, eligibility, official-alias, AGENT-visible context,
recoverability, pilot-generation, pilot-validation, and standalone recursive
grounding-validation gates are currently implemented. The method-call budget
and strict structural output contract are also frozen, and both Qwen model
repositories are pinned to remotely verified immutable revisions. The
versioned prompts, provider-independent exact-call runner, and config-bound
JSONL/ZIP checkpoint contract are now implemented. A local-only Qwen backend
and Python-process non-loopback socket guard are implemented and tested. The
pinned 3B and 7B checkpoints are cached, checksummed, and have successful
synthetic load/generation smokes. The current outputs generated one token each
and were not interpreted as plans. The earlier failed 3B load and successful
32-token 3B smoke are preserved separately. The 7B smoke required CPU and disk
offload on the local 4 GB GPU. No study case has been invoked. The
training-only pilot
contains 30 clusters and 150 cases across all 15 scenario/difficulty strata,
with 15 explicit-UAV-identity and 15 coverage-threshold interventions. Its
version 2 review packet contains one exact instruction per row plus compact
entity, UAV-status, and intervention summaries. Two separate synthetic
negative controls prove rejection of an incomplete cluster and a wrong-UAV
resource patch; they are not study data.
The returned reviewer notes begin with `Accept:` for all 150 cases. Under the
project's recorded interpretation, the completed packet assigns pseudonym `1`,
`review_status=approved`, and `case_valid=yes`; it structurally validates all
30 clusters. The original response, normalized packet, transformation audit,
and validation hashes are retained. Reviewer identity and independence are
project-attested provenance that code cannot verify. No pilot case has been
evaluated. All 600 method-first-prompt constructions over those cases pass the
stored privileged/label leakage audit without invoking a model.

The same construction has now been applied to every eligible source task. The
versioned full draft contains 1,473 clusters and 7,365 cases after 27 recorded
cross-split duplicate exclusions. Deterministic reconstruction against the
pinned source, eligibility manifest, session splits, and all compact review
rows passes. The project does not claim full row-level human review. Instead,
`expert_qc_audit_v1.json` records the balanced 30-cluster expert sample, and
`accuracy_case_manifest_v1.json` approves only the 284-cluster, 1,420-case test
matrix under explicit deterministic-label provenance. Zero gold fields enter
materialized model contexts.

`accuracy_protocol_freeze_v1.json` registers the M3-versus-M1 primary contrast,
M3-versus-M4 confirmatory contrast, two primary outcomes, failure handling,
10,000-draw source-cluster bootstrap, deterministic decoding, 11,360 expected
rows, and 17,040 expected model calls before any study inference. Hardware
warm-up is explicitly excluded from the accuracy gate and retained for the
separate resource experiment.
`scoring_contract_audit_v1.json` binds the deterministic scorer to that
protocol and manifest. It verifies all 284 hidden official-command inventories,
preserves raw model output separately from post-gate system disposition, and
records that zero checkpoint rows or study scores were read.
Context and recoverability evidence are documented in
`docs/multiuav_agent_context_protocol.md` and
`docs/multiuav_recoverability_protocol.md`.
Grounding behavior and claim limits are documented in
`docs/multiuav_grounding_validator_protocol.md`.
Runner and checkpoint behavior is documented in
`docs/multiuav_runner_checkpoint_protocol.md`.
Local model and isolation behavior is documented in
`docs/multiuav_offline_runtime_protocol.md`.

## Legacy Component Roles

- Whisper is excluded from the primary text-first experiment. Speech remains a
  separately evaluated roadmap capability.
- The Week 2 DistilBERT checkpoint is verifiably connected to the historical
  Shepherd end-to-end path through
  `scripts/run_trained_span_integrated_prototype.py`. That path assembles intent
  only from predicted spans and has a regression test that fails if the
  deterministic parser is invoked. The checkpoint remains excluded from the
  primary comparison because it was trained to tag Shepherd intent spans, not
  to produce MultiUAV API plans. Forcing it into M1-M4 would not provide a
  common or scientifically justified role.
- The Week 8 deterministic mission pipeline remains historical roadmap
  evidence. It is not M2 or M3 and must not be silently renamed as either.
- The earlier Week 9 monolithic Qwen diagnostic used development Shepherd
  evidence. It remains a historical diagnostic and is not revised-study
  evidence.

These components and results remain in Git for reproducibility and negative
evidence. Exclusion from the primary study is not deletion or a claim that the
earlier work was useless.

## Notebook Entry Point

`notebooks/Notebook9_Evaluation.ipynb` checks out
`codex/multiuav-validation-study`, audits the completed source, QC, protocol,
and case-manifest gates, and reports the blocker before model inference. It does not
invoke the legacy diagnostic runner or a model.

The executable wiring audit is:

```powershell
python scripts/audit_multiuav_study_wiring.py `
  --output outputs/multiuav/study_wiring.json
```

The output is a wiring/readiness record, not an evaluation result.

The recorded DistilBERT wiring smoke result is
`outputs/evaluations/week7_distilbert_wiring_smoke_v1.json`. It records the
checkpoint and input hashes, runtime versions, GPU, and invoked parser. It is
labelled `wiring_smoke_test_not_paper_evidence` and must not enter revised-paper
tables, figures, or comparative claims.

## Current Stop Condition

The pilot expert-QC packet, full-dataset generation, score-blind protocol,
held-out accuracy manifest, and label-separated scoring contract are complete.
Accuracy inference is blocked only until these changes are committed and final
run configurations bind that exact commit. Hardware warm-up and thermal
controls apply only to the later resource experiment. A deterministic 30-task
candidate subset, 24 condition orders, and an approval-gated resource-config
builder now exist. Static fidelity and method-case NVML instrumentation are
implemented, but neither model smoke nor the telemetry probe has produced a
revised-study result.
