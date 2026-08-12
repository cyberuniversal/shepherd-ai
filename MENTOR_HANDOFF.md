# Shepherd-AI Final Mentor Handoff

This document is the entry point for the final frozen submission. The package
adds no model, module, baseline, or research direction. It organizes the work
already completed and maps it directly to the mentor's eight requests.

## What To Submit

Submit the single ZIP named `shepherd-ai-mentor-final-<commit>.zip` from the
`dist/` directory. The ZIP contains:

- `START_HERE.md`: this checklist, rewritten for the ZIP layout;
- `repository/`: the complete tracked Shepherd-AI source repository;
- `deliverables/`: the IEEE manuscript and editable presentation;
- `evidence/`: surfaced raw checkpoints, failed attempts, processed results,
  session statistics, review records, tables, and figures;
- `FILE_INVENTORY.tsv`: path, byte count, and SHA-256 for every ZIP payload;
- `COMMIT.txt`: the exact Git commit represented by the package.

The complete repository is also available from the GitHub branch
`codex/multiuav-validation-study`. `COMMIT.txt` is authoritative for the exact
submitted revision.

## Mentor Request Checklist

### 1. Complete Source Code

Status: complete.

The full tracked repository is under `repository/`. Important final-study code
is located at:

- M1-M4 definitions: `src/shepherd_ai/multiuav_methods.py`
- M1-M4 execution: `src/shepherd_ai/multiuav_runner.py`
- prompts: `src/shepherd_ai/multiuav_prompts.py`
- strict plan contract: `src/shepherd_ai/multiuav_plan_contract.py`
- evidence ledger contract: `src/shepherd_ai/multiuav_ledger_contract.py`
- grounding validator: `src/shepherd_ai/multiuav_grounding_validator.py`
- scoring: `src/shepherd_ai/multiuav_scoring.py`
- checkpoints and resume: `src/shepherd_ai/multiuav_checkpoints.py`
- dataset construction: `src/shepherd_ai/multiuav_interventions.py` and
  `src/shepherd_ai/multiuav_evaluation_data.py`
- accuracy and resource analysis: `src/shepherd_ai/multiuav_study_analysis.py`
  and `src/shepherd_ai/multiuav_resource_analysis.py`
- command-line entry points: `scripts/`
- tests: `tests/`

Dependency specifications are `requirements.txt` and `pyproject.toml`.

### 2. Raw Outputs, IDs, Failures, Tables, Figures, And Commands

Status: complete.

Surfaced raw evidence is under `evidence/raw/`:

- `qwen25_3b_accuracy_checkpoint.zip`: 5,680 raw method-case rows plus the
  frozen run configuration;
- `qwen25_7b_accuracy_checkpoint.zip`: 5,680 raw method-case rows plus the
  frozen run configuration;
- `resource_campaign_attempt3_complete.tar.gz`: 3,600 resource rows across
  24 conditions, including run summaries and start-control records;
- `failed_attempts/`: preserved failed, interrupted, and preempted attempts.

The accuracy run summaries do not define a separate runtime `session_id`; no
identifier was invented. The 15 benchmark source-session IDs and all
model-method session statistics are in
`evidence/session_ids/multiuav_accuracy_session_statistics_v1.csv`. Resource
condition and start-control IDs remain in the raw campaign archive.

Scored failure identifiers and flags are in
`evidence/failures/multiuav_accuracy_failure_cases_v1.zip`. The short failure
report and machine-readable counts are in the same directory. Final CSV tables
are under `evidence/tables/`, and publication PNG/PDF figures are under
`evidence/figures/`. Exact reconstruction, inference, admission, scoring,
analysis, and manuscript commands are in
`evidence/commands/final_reproduction_commands.md`.

Raw model text is preserved in the raw checkpoint archives. It is not copied
into descriptive session or failure artifacts.

### 3. Final Pipeline Architecture

Status: complete.

The authoritative architecture is
`evidence/architecture/final_pipeline_architecture.md`. The final reported
path is text-first M1-M4 inference with pinned Qwen2.5 3B/7B checkpoints,
strict parsing, deterministic validation, score-blind admission, static plan
fidelity and containment scoring, source-cluster bootstrap, and descriptive
session/failure analysis.

Whisper, DistilBERT, and vision are not integrated into the final M1-M4
experiment. They are retained in the complete repository only as preliminary
roadmap work and are excluded from the paper's final claims.

### 4. Reviewed CSV Comments

Status: complete.

The exact returned review file is
`evidence/review/multiuav_intervention_pilot_review_response_2026-08-04.csv`.
The normalized 150-row reviewed record is
`evidence/review/multiuav_intervention_pilot_review_completed_v2.csv`.
The resolution ledger is `evidence/review/multiuav_review_resolution_final.md`.

All 150 rows were accepted. The ledger records eight wording notes about
"assign" versus "assigned," 27 duplicated "Drone" tokens, and one fixed-
coordinate wording conflict. Those source-text defects were disclosed and not
silently rewritten after inference, because rewriting evaluated prompts would
break checkpoint and hash correspondence.

### 5. Essential Remaining Analysis

Status: complete.

The session-level statistics and bounded 3B/7B failure analysis are included:

- `evidence/session_ids/multiuav_accuracy_session_statistics_v1.csv`
- `evidence/failures/multiuav_accuracy_failure_analysis_v1.json`
- `evidence/failures/multiuav_accuracy_failure_analysis_v1.md`

The central negative result is explicit: all model-method combinations had
zero static plan fidelity on all 852 executable cases per method. The reported
7B M3 strict successes are containment outcomes on non-executable cases, not
successful executable plans.

### 6. Required Terminology

Status: complete.

M4 is described as **model-call-count-matched**. Plan-quality outcomes are
described as **static plan fidelity** because no official MultiUAV server,
robotics simulator, or physical-drone execution was performed.

### 7. Final Manuscript

Status: complete.

The final paper is under `deliverables/manuscript/` in Markdown, IEEE
conference-format LaTeX, and PDF form. It contains numeric references, clear
limitations, registered accuracy figures, exploratory resource figures, and
only claims supported by completed experiments. The traceability audit is
included under `evidence/audits/`.

### 8. One Final Project Package

Status: complete when the ZIP checksum and inventory verification pass.

The package includes code, README files, requirements, raw and processed
results, session IDs, failed attempts, tables, figures, the manuscript in
`.tex` and PDF formats, and the editable `.pptx` presentation. The file
inventory provides a SHA-256 digest for every payload.

## Final Claim Boundary

The completed experiment supports a narrow systems-and-measurement claim:
validation placement changed failure containment and measured local inference
cost under the frozen static MultiUAV-Plat derivative benchmark, with effects
that differed between Qwen2.5-3B and Qwen2.5-7B. It does not demonstrate
correct executable plans, simulator success, physical-drone safety, deployment
readiness, or generality beyond the tested models and tasks.

The historical external-review packet remains in the complete repository for
provenance. Its `external review pending` status is superseded by the mentor's
instruction that no additional external review is required before concluding
mentor review.

## Verification Record

Before packaging, the final repository must pass:

```powershell
python -m pytest -q
python -m ruff check scripts/analyze_multiuav_accuracy.py scripts/build_final_manuscript.py src/shepherd_ai/multiuav_study_analysis.py src/shepherd_ai/multiuav_manuscript_audit.py src/shepherd_ai/multiuav_external_review.py tests/test_multiuav_study_analysis.py tests/test_multiuav_manuscript_audit.py
python scripts/audit_multiuav_manuscript.py
python scripts/build_final_manuscript.py
```

The final ZIP must then pass complete inventory and SHA-256 verification.
