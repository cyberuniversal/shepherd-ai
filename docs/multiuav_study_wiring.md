# MultiUAV Validation Study Wiring

## Active Path

The primary revised experiment is text-first:

```text
frozen MultiUAV source task
  -> approved five-variant case (none exists; training pilot review pending)
  -> method M1, M2, M3, or M4
  -> strict API-plan parser
  -> deterministic evidence, provenance, and safety validation
  -> selected static or official-server execution scope
  -> label-separated scoring and resource measurement
```

The source, split, eligibility, official-alias, AGENT-visible context,
recoverability, pilot-generation, pilot-validation, and standalone recursive
grounding-validation gates are currently implemented. The method-call budget
and strict structural output contract are also frozen, and both Qwen model
repositories are pinned to remotely verified immutable revisions. The
versioned prompts, provider-independent exact-call runner, and config-bound
JSONL/ZIP checkpoint contract are now implemented. The training-only pilot
contains 30 clusters and 150 cases across all 15 scenario/difficulty strata.
All 30 clusters remain pending human review; none is approved, runnable, or
evaluated. All 600 method-first-prompt constructions over those cases pass the
stored privileged/label leakage audit without invoking a model.
Context and recoverability evidence are documented in
`docs/multiuav_agent_context_protocol.md` and
`docs/multiuav_recoverability_protocol.md`.
Grounding behavior and claim limits are documented in
`docs/multiuav_grounding_validator_protocol.md`.
Runner and checkpoint behavior is documented in
`docs/multiuav_runner_checkpoint_protocol.md`.

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
`codex/multiuav-validation-study`, audits the completed source and pilot gates,
and reports the blockers before human review and model inference. It does not
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

The pilot is ready for real human review. Revised-study model inference remains
blocked until pilot review/adjudication, full intervention generation and
review, local model loading and isolation checks, execution scope, and hardware
protocol are frozen and tested. Prompts, method orchestration, strict parsing,
recursive validation, and checkpoint/resume are connected and tested only with
scripted synthetic backends; they have not produced revised-study results.
