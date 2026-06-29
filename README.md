# Shepherd-AI

Shepherd-AI is a planned Python research prototype for natural-language multi-drone mission planning and coordination in software simulation.

Current status: this repository contains project source documents, a deterministic typed-command intent parser baseline, and a speech-input scaffold for audio manifest validation and transcript evaluation. It is not an end-to-end prototype, does not control physical drones, and does not yet implement Whisper inference, grounding, planning, scheduling, vision, safety validation, or integrated mission execution.

## Project Rule

The roadmap is used for sequence and broad scope. The literature review is used for actual technical implementation decisions.

That means Shepherd-AI should not stop at hand-written demos when the reviewed papers indicate that training, domain adaptation, deterministic validation, structured representations, or held-out evaluation are required. Baselines are allowed, but they must be labeled as baselines and compared against trained or literature-supported approaches when the data exists.

## Source Documents

The current source of truth is:

- `AGENTS.md`
- `docs/roadmap.pdf`
- `docs/literature_review/ExportBlock-44375080-06b3-45d5-a3ed-ac880ba80cd6-Part-1.zip`
- `docs/project_synthesis.md`
- `docs/implementation_plan.md`
- `docs/milestone_2_speech_input.md`
- `docs/literature_to_implementation.md`

The roadmap path is `docs/roadmap.pdf`; there is currently no `docs/roadmap/` directory.

## Google Colab Structure

The repository now includes the roadmap's Colab-style notebook sequence:

- `notebooks/Notebook1_Setup.ipynb`
- `notebooks/Notebook2_NLP.ipynb`
- `notebooks/Notebook3_Grounding.ipynb`
- `notebooks/Notebook4_Planner.ipynb`
- `notebooks/Notebook5_Scheduler.ipynb`
- `notebooks/Notebook6_Vision.ipynb`
- `notebooks/Notebook7_Safety.ipynb`
- `notebooks/Notebook8_FinalDemo.ipynb`
- `notebooks/Notebook9_Evaluation.ipynb`

Notebooks should orchestrate Colab workflows. Reusable implementation belongs in `src/shepherd_ai/`, with tests in `tests/`.

Dataset and artifact locations:

- `datasets/commands/`
- `datasets/sample_audio/`
- `datasets/maps/`
- `datasets/aerial_images/`
- `outputs/`
- `reports/`

## First Milestone

The first implemented milestone is a typed-command intent extraction baseline from Week 2 of the roadmap. It accepts simple typed mission commands and emits JSON fields aligned with the roadmap: `action`, `count`, `location`, `target`, and `constraints`.

Audio support is deferred because the repository has no sample WAV files, transcripts, Whisper configuration, package versions, or evaluation split.

## Speech Input Scaffold

Milestone 2 currently validates audio/transcript manifests and evaluates transcript text. It does not run Whisper yet.

Manifest records should point to WAV files under the dataset root and include transcript provenance fields. See `docs/milestone_2_speech_input.md`.

The current parser and transcript utilities are not trained models. A serious Week 2 implementation needs labeled command data, split definitions, and a trained or fine-tuned intent extraction component, with deterministic baselines retained for comparison.

## Week 2 Intent Training

The first supervised intent-extraction baseline is documented in `docs/week2_intent_training.md`.

Run:

```powershell
python scripts/train_intent_model.py --dataset datasets/commands/intent_labeled_synthetic.jsonl --model-output outputs/model_artifacts/intent_nb_v0.json --metrics-output outputs/evaluations/intent_nb_v0_metrics.json --comparison-output outputs/evaluations/intent_nb_v0_vs_deterministic.json --seed 17
```

Current synthetic held-out result:

- `trained_nb_v0`: field accuracy 0.85, exact-record accuracy 0.25.
- `deterministic_v0`: field accuracy 1.0, exact-record accuracy 1.0 on the same tiny synthetic test split.

This is an early synthetic baseline and not a real-user or speech-recognition result.

## Run Tests

Use Python from the repository root:

```powershell
python -m unittest discover -s tests
```

## Run Example

```powershell
python examples/intent_baseline_example.py
```

## Run Initial Evaluation

```powershell
python scripts/evaluate_intent_baseline.py
```

The evaluation writes raw output to `outputs/evaluations/intent_baseline_roadmap_examples.json`. The included sample is roadmap-derived and synthetic; it is a smoke check, not a research benchmark.
