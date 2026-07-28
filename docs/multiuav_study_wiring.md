# MultiUAV Validation Study Wiring

## Active Path

The primary revised experiment is text-first:

```text
frozen MultiUAV source task
  -> frozen five-variant case (not yet generated)
  -> method M1, M2, M3, or M4
  -> strict API-plan parser
  -> deterministic evidence, provenance, and safety validation
  -> selected static or official-server execution scope
  -> label-separated scoring and resource measurement
```

The source, split, eligibility, official-alias, AGENT-visible context, and
recoverability gates are currently implemented. The study is ready for draft
intervention generation, but no generated case is approved or evaluated.
Context and recoverability evidence are documented in
`docs/multiuav_agent_context_protocol.md` and
`docs/multiuav_recoverability_protocol.md`.

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

`notebooks/Notebook9_Evaluation.ipynb` now checks out
`codex/multiuav-validation-study`, audits the completed source gates, and
reports the blockers before intervention generation. It does not invoke the
legacy diagnostic runner or a model.

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

Revised-study model inference remains blocked until the intervention dataset,
method call budgets, plan contract, recursive validators, immutable Qwen
revisions, isolation checks, execution scope, and hardware protocol are frozen
and tested.
