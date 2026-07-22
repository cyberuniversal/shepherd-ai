# Week 9 Paper-Draft Protocol

## Why This Milestone Comes Next

The roadmap places research-paper drafting immediately after the Week 8
end-to-end demonstration and evaluation. Week 8 now has a completed,
machine-checked evidence bundle, so the manuscript can describe implemented
work and measured results without substituting plans for evidence.

## Objective

Produce the roadmap's first paper draft with a title, abstract and keywords,
introduction, motivation, problem statement, objectives, related work,
proposed method, system architecture, and methodology. Prepare architecture
and workflow figures, dataset and module tables, and an organized bibliography.

## Evidence Rules

- Shepherd-AI result claims must trace to committed evaluation artifacts.
- Related-work claims must trace to the repository literature-review export.
- Paper numbers are generated from stored JSON rather than copied manually.
- Negative and null results remain visible.
- Development, validation, and held-out results retain their original labels.
- A completed software workflow is not evidence of physical flight or safety.
- No novelty claim is made because the repository has not established one.
- The fixed Week 8 run is one development scenario, not a statistical
  end-to-end benchmark.

## Inputs

- `docs/roadmap.pdf`
- The complete Markdown literature-review export stored in
  `docs/literature_review/ExportBlock-44375080-06b3-45d5-a3ed-ac880ba80cd6-Part-1.zip`
- `docs/literature_to_implementation.md`
- `outputs/evaluations/week8_completion_gate_audit.json`
- `outputs/evaluations/week8_end_to_end_evaluation.json`
- The raw Week 8 artifacts referenced by those files

Licensed imagery, audio, and model weights remain outside Git. Their registered
hashes, split roles, model metadata, and derived predictions are used instead.

## Deliverables

- `reports/shepherd_ai_paper_draft.md`
- `reports/week9_bibliography.md`
- `reports/figures/week9_system_architecture.mmd`
- `reports/figures/week9_evaluation_workflow.mmd`
- `reports/figures/week9_stage_runtime.png`
- `outputs/tables/week9_end_to_end_metrics.csv`
- `outputs/tables/week9_runtime_stages.csv`
- `outputs/evaluations/week9_paper_evidence.json`
- `reports/week9_evidence_traceability.md`
- A reproducible `notebooks/Notebook9_Evaluation.ipynb`

## Completion Criteria

Week 9 is complete only when all roadmap draft sections exist, every numeric
Shepherd-AI claim is traceable to registered evidence, every related-work entry
comes from the repository export, figures and tables are reproducible, known
limitations are explicit, and the documented checks pass. Venue formatting,
the formal research question, and a defensible novelty claim remain
unspecified and cannot be invented during this milestone.
