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

Only the source, split, eligibility, and official-alias gates are currently
implemented. The remaining stages above are planned and must not be described
as wired or evaluated.

## Legacy Component Roles

- Whisper is excluded from the primary text-first experiment. Speech remains a
  separately evaluated roadmap capability.
- The Week 2 DistilBERT checkpoint is excluded because it was trained to tag
  Shepherd intent spans, not to produce MultiUAV API plans. Forcing it into the
  revised comparison would not give M1-M4 a common or scientifically justified
  role.
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

## Current Stop Condition

Revised-study model inference remains blocked until the context projection,
recoverability rule, intervention dataset, method call budgets, plan contract,
recursive validators, immutable Qwen revisions, isolation checks, execution
scope, and hardware protocol are frozen and tested.
