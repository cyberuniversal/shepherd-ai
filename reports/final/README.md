# Shepherd-AI Final Mentor-Review Package

This package freezes the completed validation-placement study. It adds no new
model, baseline, module, or research direction.

## Final Claim Boundary

The final M1-M4 experiment is text-first. It compares monolithic,
deterministic post-plan, stage-wise, and model-call-count-matched post-plan
validation with pinned Qwen2.5 3B and 7B checkpoints. Outcomes use static plan
fidelity and containment. No official MultiUAV server, robotics simulator, or
physical drone executed the generated plans.

Whisper, DistilBERT, and vision are historical preliminary components. They
are preserved in the repository but are excluded from the final paper's M1-M4
claims.

## Primary Deliverables

- Markdown manuscript: `reports/multiuav_validation_placement_manuscript_v1.md`
- LaTeX manuscript: `reports/final/shepherd_ai_manuscript.tex`
- PDF manuscript: `reports/final/shepherd_ai_manuscript.pdf`
- Presentation: `reports/final/shepherd_ai_presentation.pptx`
- Presentation preview: `reports/final/shepherd_ai_presentation_montage.webp`
- Final architecture: `docs/final_pipeline_architecture.md`
- Reproduction commands: `docs/final_reproduction_commands.md`
- Reviewer resolution: `docs/multiuav_review_resolution_final.md`
- Requirements: `requirements.txt` and `pyproject.toml`

## Run Identity And Raw Evidence

| Run | Frozen identity | Raw evidence |
|---|---|---|
| Qwen2.5-3B accuracy | revision `aa8e72537993ba99e69dfaafa59ed015b17504d1`; execution commit `456b864d6b0dd9dce5da5a5fdcb497bfc0510a37`; 5,680 rows | `datasets/multiuav_plat/nautilus/qwen25_3b_accuracy_complete_v1/` |
| Qwen2.5-7B accuracy | revision `a09a35458c702b33eeacc393d103063234e8bc28`; execution commit `456b864d6b0dd9dce5da5a5fdcb497bfc0510a37`; 5,680 rows | `datasets/multiuav_plat/nautilus/qwen25_7b_accuracy_complete_v1/` |
| Resource attempt 3 | job `shepherd-ai-resource-v1-a3`; pod `shepherd-ai-resource-v1-a3-sszxb`; RTX 3090; 24 conditions; 3,600 rows | `datasets/multiuav_plat/nautilus/resource_campaign_attempt3_complete/` |

The accuracy run summaries do not define a separate runtime `session_id`; this
package does not invent one. The 15 evaluated benchmark session IDs are listed
for every model-method combination in
`outputs/tables/multiuav_accuracy_session_statistics_v1.csv`. Resource
condition/start-control identifiers are preserved inside the admitted raw
campaign archive and admission record.

## Failures And Negative Results

- Preserved infrastructure and interrupted attempts:
  `datasets/multiuav_plat/failed_attempts/`
- Scored failure-case identifiers and flags:
  `outputs/evaluations/multiuav_accuracy_failure_cases_v1.zip`
- Aggregate failure counts:
  `outputs/evaluations/multiuav_accuracy_failure_analysis_v1.json`
- Human-readable failure analysis:
  `reports/multiuav_accuracy_failure_analysis_v1.md`

Raw model text is retained only in the sealed checkpoints. It is not duplicated
into the descriptive failure files.

## Final Tables And Figures

Accuracy and resource tables are under `outputs/tables/`. Registered accuracy
and exploratory resource figures are under `reports/figures/`. Their
source-bound manifests are:

- `outputs/evaluations/multiuav_accuracy_figures_v1/manifest.json`
- `outputs/evaluations/multiuav_resource_reporting_v1/manifest.json`

## Source Code Coverage

The repository includes the M1-M4 implementations, prompts, strict parsers,
grounding and safety validators, dataset-generation scripts, model runner,
checkpoint/resume logic, admission gates, scoring, bootstrap analysis,
resource analysis, tests, notebooks, and Kubernetes manifests. The upstream
MultiUAV-Plat checkout and model weights are not vendored; their immutable
revisions and acquisition instructions are recorded. Licensed Week 6 imagery
is also not redistributed and is outside the final M1-M4 study.

## Verification

The final handoff is valid only when the full test suite, scoped Ruff check,
manuscript
traceability audit, PDF inspection, presentation layout inspection, package
inventory, and SHA-256 manifest pass. The ZIP root includes the final Git
commit identifier and checksums for every packaged file.

Whole-repository Ruff is not claimed as passing; it reports 40 preserved
findings in historical files outside this closeout. The final package records
that residual debt rather than modifying unrelated work.
