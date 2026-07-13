# Roadmap Status

This file is the repository index for matching GitHub structure to the roadmap.
It should be updated when a roadmap week starts, completes, or changes scope.

## Branch Policy

`main` should contain coherent roadmap milestones, not partial experiment dumps.
Active work branches should use milestone-oriented names:

- `codex/week1-setup`
- `codex/week2-speech-intent`
- `codex/week3-grounding`
- `codex/week4-planning`
- `codex/week5-scheduling`
- `codex/week6-vision`
- `codex/week7-safety-integration`
- `codex/repo-hygiene`

Old branches should be deleted after their work is merged and traceable through
commits or pull requests. Branches are work lanes; the lasting architecture is
the roadmap-indexed docs, notebooks, source modules, tests, and curated fixtures.

## Source-Control Rule

Tracked by default:

- source code,
- scripts,
- tests,
- notebooks,
- docs,
- small curated datasets and manifests needed for reproducibility.

Ignored by default:

- generated `outputs/`,
- generated `reports/`,
- model checkpoints,
- raw audio/media,
- downloaded public datasets,
- local helper scripts and backups.

See `docs/repository_hygiene.md`.

## Milestone Index

| Roadmap week | Scope | Main modules/scripts | Notebook | Data fixtures | Gate/status |
|---|---|---|---|---|---|
| Week 1 | Repository setup and project understanding | `pyproject.toml`, `README.md`, `docs/project_synthesis.md`, `docs/implementation_plan.md` | `notebooks/Notebook1_Setup.ipynb` | Directory READMEs | Partially complete; richer setup journal still useful |
| Week 2 | Speech recognition and intent extraction | `src/shepherd_ai/intent.py`, `audio_manifest.py`, `intent_training.py`, `span_training.py`, `span_annotations.py`, `constraint_normalization.py`; Week 2 scripts | `notebooks/Notebook2_NLP.ipynb`, `notebooks/Notebook2_NLP_Colab_T4.ipynb` | `datasets/commands/`, audio manifests under `datasets/sample_audio/` | `outputs/evaluations/week2_completion_gate_audit.json`; currently passed locally after fresh benchmark |
| Week 3 | Command grounding and map representation | `src/shepherd_ai/grounding.py`, `grounding_dataset.py`, `grounding_coverage.py`, `grounding_clarification.py`, `map_validation.py`, `map_visualization.py`, `week3_*` | `notebooks/Notebook3_Grounding.ipynb` | `datasets/maps/` | `outputs/evaluations/week3_completion_gate_audit.json`; synthetic-map gate passed locally |
| Week 4 | Mission planning | `src/shepherd_ai/mission_planning.py`, `scripts/plan_mission.py`, `scripts/evaluate_mission_planning.py`, `scripts/render_mission_flow.py`, `scripts/audit_week4_completion.py` | `notebooks/Notebook4_Planner.ipynb` | `datasets/maps/week4_planning_cases_v1.jsonl` | `outputs/evaluations/week4_completion_gate_audit.json`; planning gate passed locally |
| Week 5 | Multi-drone scheduling | `src/shepherd_ai/scheduling.py`, `scripts/schedule_missions.py`, `scripts/audit_week5_completion.py` | `notebooks/Notebook5_Scheduler.ipynb` | `datasets/drones/week5_three_drone_fleet_v1.json` | `outputs/evaluations/week5_completion_gate_audit.json`; scheduling gate passed locally |
| Week 6 | Computer vision integration | `src/shepherd_ai/vision.py`, `src/shepherd_ai/segmentation.py`, Week 6 preparation, validation, detection, and segmentation-training scripts | `notebooks/Notebook6_Vision.ipynb` | Agriculture-Vision selected; licensed imagery and checkpoints remain outside Git | T4 smoke test and 64/64 segmentation development run recorded; scaling, imbalance experiments, and fixed held-out evaluation remain |
| Week 7 | Safety, feedback, and integration | Not implemented | `notebooks/Notebook7_Safety.ipynb` | Not specified | Not started |
| Week 8 | End-to-end demo and evaluation | Not implemented | `notebooks/Notebook8_FinalDemo.ipynb`, `notebooks/Notebook9_Evaluation.ipynb` | Depends on Weeks 2-7 | Not started |
| Week 9 | Research paper draft | Not implemented | Not stated | Evaluation artifacts and figures | Not started |
| Week 10 | Final paper and presentation | Not implemented | Not stated | Final reports/slides | Not started |

## Current Caveats

- The current local branch contains several roadmap weeks because the work was
  originally built in one long branch. Future branches should be smaller and
  milestone-named.
- Generated local outputs remain on disk for research continuity, but they are
  removed from normal Git tracking.
- Completion gates under `outputs/` are regenerated artifacts. If a gate result
  must be included in a paper or review, promote the specific artifact
  deliberately with `git add -f` and explain why.
- Week 6 has a dataset-backed validation-only development result. It is not a
  final benchmark: the 64/64 run reached modified mIoU `0.0965`, mostly from
  background, and did not learn most anomaly classes.
