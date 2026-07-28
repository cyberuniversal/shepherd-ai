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
- `codex/week8-end-to-end`
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
| Week 6 | Computer vision integration | `src/shepherd_ai/vision.py`, `src/shepherd_ai/segmentation.py`, Week 6 preparation, validation, detection, and segmentation-training scripts | `notebooks/Notebook6_Vision.ipynb` | Agriculture-Vision and VisDrone2019-DET; licensed imagery and checkpoints remain outside Git | Complete for roadmap advancement; registered 50-epoch VisDrone YOLOv8n validation baseline and Agriculture-Vision segmentation development comparisons recorded |
| Week 7 | Safety, feedback, and integration | `src/shepherd_ai/safety.py`, `feedback.py`, `integration.py`, `clarification_dialogue.py`, `mission_supervision.py`, `integrated_prototype.py`; Week 7 evaluation and audit scripts | `notebooks/Notebook7_Safety.ipynb` | Synthetic policy plus preflight, dialogue, route, supervision, integration, and sensitivity cases under `datasets/safety/` | Complete for roadmap advancement under the corrected gate; all registered evaluations pass and the audit has no blockers |
| Week 8 | End-to-end demo and evaluation | `src/shepherd_ai/mission_decomposition.py`, `src/shepherd_ai/week8_pipeline.py`, `src/shepherd_ai/mission_simulation.py`, `src/shepherd_ai/week8_asr.py`, `src/shepherd_ai/week8_evaluation.py`, `src/shepherd_ai/week8_vision_evaluation.py`, `src/shepherd_ai/week8_completion.py`, Week 8 run/evaluation/audit scripts | `notebooks/Notebook8_FinalDemo.ipynb` | Existing map/fleet/policy; exact human WAV and private Agriculture-Vision/checkpoint assets | Complete for roadmap advancement; all ten completion gates pass and the five required metrics are stored with raw evidence |
| Week 9 | Research paper draft | `src/shepherd_ai/week9_paper.py`, `src/shepherd_ai/week9_completion.py`, Week 9 build and audit scripts | `notebooks/Notebook9_Legacy_Paper_Artifacts.ipynb` | Promoted Week 8 evidence; generated paper tables and figures | Complete historical roadmap evidence; all eight paper-draft and traceability gates pass. The active `Notebook9_Evaluation.ipynb` is now reserved for the revised MultiUAV study. |
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
- Week 6 is complete at the roadmap milestone level. The registered VisDrone
  detector reached validation mAP50-95 `0.16724`; this is a completed baseline,
  not a state-of-the-art claim. Agriculture-Vision remains development-only:
  the leading fixed 256/256 BCE-Dice result reached modified mIoU `0.15387`,
  with drydown as the only anomaly class with nonzero IoU.
- Week 7 is complete at the software-simulation roadmap level after the
  corrected gate. Evidence includes `12/12` preflight, `4/4` dialogue, `3/3`
  route, `8/8` supervision, `3/3` integration, and `4/4` sensitivity results.
  These are registered development cases, not physical safety or Week 8
  end-to-end mission performance.
- Week 8 is complete for roadmap advancement. The fixed command produced two
  clauses, three assignments, 43 deterministic telemetry records, and an
  approved software-simulation safety report after the operator resolved the
  irrigation clause to East Field. Exact-scenario Whisper evaluation recorded
  WER `0.07143`; trained intent exact match was `1/2` with `9/10` fields;
  grounding accuracy was `2/2`; scheduling completion was `3/3`; and measured
  warm-model pipeline time was `31.3343` seconds. Mission-assigned evaluation
  on 59 disjoint Agriculture-Vision validation-remainder images produced
  modified mean IoU `0.02356`, a weak generalization result that remains part
  of the evidence. The run is a single development scenario, not a statistical
  end-to-end benchmark. It does not demonstrate physical flight, guarantee
  safety, or establish novelty. The discontinued Three.js and Gazebo reports
  remain historical negative evidence and are not active architecture.
- Week 9 is complete for historical roadmap advancement, not publication
  readiness. The
  first draft contains every section named by the roadmap, architecture and
  evaluation workflow diagrams, dataset and module tables, a generated runtime
  figure, five-metric traceability, and an organized bibliography covering all
  15 reviewed papers. The completion audit passes eight gates with no blockers.
  The active paper has since been replaced by the proposed MultiUAV-Plat
  validation-placement study in
  `docs/multiuav_validation_study_protocol.md`. That revision supplies a
  bounded proposed question but still lacks a finalized protocol, implemented
  benchmark, locked evaluation, final results discussion, and final paper
  formatting.
