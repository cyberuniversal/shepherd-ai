# Final Mentor Handoff

This repository is the final, frozen publication package for **"Validation
Placement in Static Multi-UAV Language Planning: A Paired Failure-Containment
and Compute Study."** No external review or scope expansion is required before
the concluding mentor review.

## Submission Contents

- Final IEEE manuscript: `paper/main.tex` and `paper/main.pdf`
- Final presentation: `presentation/validation_placement_presentation.pptx`
- M1-M4 implementation: `src/shepherd_ai/multiuav_*.py`
- Dataset generation and validation: `scripts/*multiuav*.py`
- Frozen prompts, run configurations, splits, and labels:
  `datasets/multiuav_plat/`
- Raw accuracy checkpoints and run summaries:
  `datasets/multiuav_plat/nautilus/`
- Failed and interrupted attempts:
  `datasets/multiuav_plat/failed_attempts/`
- Processed results and provenance: `outputs/`
- Session statistics: `outputs/tables/multiuav_accuracy_session_statistics_v1.csv`
- Failure cases and analysis:
  `outputs/evaluations/multiuav_accuracy_failure_cases_v1.zip` and
  `reports/multiuav_accuracy_failure_analysis_v1.md`
- Final tables and figures: `outputs/tables/` and `reports/figures/`
- Reviewed pilot records and resolution:
  `reports/multiuav_intervention_pilot_review_completed_v2.csv` and
  `docs/multiuav_review_resolution_final.md`
- Exact commands: `docs/final_reproduction_commands.md`
- Pipeline boundary: `docs/final_pipeline_architecture.md`

## Final Claim Boundary

M4 is model-call-count-matched. Plan outcomes are static plan fidelity because
the official MultiUAV server, a robotics simulator, and physical drones were not
used. Whisper, DistilBERT, and vision are not integrated into M1-M4.

The experiment supports a bounded systems-and-measurement claim: validation
placement changed failure containment and local inference cost under the frozen
static MultiUAV-Plat derivative benchmark, and the observed effects differed
between the tested Qwen2.5 model sizes. It does not establish deployment safety,
physical mission success, or generality beyond the tested models and tasks.

## Verification

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python -m ruff check src scripts tests paper/build_resource_figure.py
python scripts/audit_multiuav_manuscript.py
Set-Location paper
python build_resource_figure.py
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

