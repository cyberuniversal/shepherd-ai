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
- `docs/week2_data_collection_protocol.md`
- `docs/week2_training_explainer.md`
- `docs/week2_span_annotation.md`

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

Notebooks should orchestrate Colab workflows. Reusable implementation belongs in `src/shepherd_ai/`, with tests in `tests/`. Transformer fine-tuning is Colab-first and should use a GPU runtime, not local CPU training.

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

Run the preserved weak baseline:

```powershell
python scripts/train_intent_model.py --dataset datasets/commands/intent_labeled_synthetic.jsonl --model-output outputs/model_artifacts/intent_nb_v0.json --metrics-output outputs/evaluations/intent_nb_v0_metrics.json --comparison-output outputs/evaluations/intent_nb_v0_vs_deterministic.json --validation-output outputs/evaluations/intent_nb_v0_validation_metrics.json --seed 17
```

Run the improved Week 2 baseline:

```powershell
python scripts/train_intent_model.py --dataset datasets/commands/intent_labeled_synthetic.jsonl --model-output outputs/model_artifacts/intent_nb_v1.json --metrics-output outputs/evaluations/intent_nb_v1_metrics.json --comparison-output outputs/evaluations/intent_nb_v1_vs_deterministic.json --validation-output outputs/evaluations/intent_nb_v1_validation_metrics.json --seed 17 --model-name trained_nb_v1 --model-version 0.2 --include-bigrams --include-alias-features --alias-feature-weight 3
```

Current synthetic held-out result:

- `trained_nb_v0`: test field accuracy 0.85, exact-record accuracy 0.25; validation field accuracy 0.95, exact-record accuracy 0.75.
- `trained_nb_v1`: test field accuracy 1.0, exact-record accuracy 1.0; validation field accuracy 1.0, exact-record accuracy 1.0.
- `deterministic_v0`: field accuracy 1.0, exact-record accuracy 1.0 on the same tiny synthetic test split.

The `trained_nb_v1` result comes from a tiny synthetic test split and field-specific schema-alias features. It is a reproducible Week 2 training workflow check, not a real-user or speech-recognition result.

Current deterministic parser status: new parser outputs are labeled `deterministic_v1`. This version adds an open-vocabulary target phrase fallback for supported Week 2 actions so commands such as `inspect the livestock pen` or `capture images of the red pickup truck` do not require every target to be hard-coded first. It is still a deterministic baseline, not a trained model.

Current curated user-command result:

- Dataset: `datasets/commands/human_written_commands_curated_v1.jsonl`
- Split: 30 train, 10 validation, 10 test.
- `trained_nb_human_curated_v1`: validation field accuracy 0.78, test field accuracy 0.70.
- `trained_nb_human_curated_v2`: validation field accuracy 1.0, test field accuracy 1.0.
- `deterministic_v0`: test field accuracy 1.0, exact-record accuracy 1.0.

`trained_nb_human_curated_v1` is the preserved negative result for the trained field classifier. `trained_nb_human_curated_v2` is a hybrid parser-gated baseline with deterministic rule overrides, not proof that a pure trained model solved the task.

The deterministic metrics above are historical outputs generated before the `deterministic_v1` parser label. Rerun the evaluation scripts to generate fresh raw artifacts for the current parser.

Evaluate a saved model on a selected split without retraining:

```powershell
python scripts/evaluate_intent_model.py --model outputs/model_artifacts/intent_nb_v1.json --dataset datasets/commands/intent_labeled_synthetic.jsonl --split validation --output outputs/evaluations/intent_nb_v1_saved_model_validation.json
```

Week 2 data collection rules are documented in `docs/week2_data_collection_protocol.md`. The current training method and suggested paper reading order are documented in `docs/week2_training_explainer.md`.

Span annotation for stronger slot extraction is documented in `docs/week2_span_annotation.md`. The repository now includes a dependency-free validator and BIO exporter for future spaCy or Hugging Face token-classification work:

```powershell
python scripts/create_span_record.py --output datasets/commands/human_verified_span_commands.jsonl --id span_cmd_001 --text "Send the nearest drone to inspect the livestock pen without crossing the road." --split train --target-span "livestock pen" --constraint-span "without crossing the road" --action-span "inspect"
python scripts/create_span_record_from_command.py --input datasets/commands/human_written_commands_curated_v1.jsonl --id human_cmd_001 --output datasets/commands/human_verified_span_commands.jsonl --count-span "two drones" --location-span "north" --action-span "inspect" --target-span "crops"
python scripts/rebuild_span_dataset_from_commands.py --commands-file span_label_commands.txt --output datasets/commands/human_verified_span_commands.jsonl --summary-output outputs/evaluations/human_verified_span_commands_summary.json --bio-output outputs/evaluations/human_verified_span_commands_bio.jsonl
python scripts/validate_span_dataset.py --dataset datasets/commands/human_verified_span_commands.jsonl --summary-output outputs/evaluations/human_verified_span_commands_summary.json --bio-output outputs/evaluations/human_verified_span_commands_bio.jsonl
```

This command requires a real span-labeled dataset. Do not treat parser drafts or assistant-curated record labels as human-verified span labels.

Train the initial supervised BIO span tagger:

```powershell
python scripts/train_span_tagger.py --dataset datasets/commands/human_verified_span_commands.jsonl --model-output outputs/model_artifacts/span_nb_v0.json --metrics-output outputs/evaluations/span_nb_v0_metrics.json --validation-output outputs/evaluations/span_nb_v0_validation_metrics.json --seed 17 --model-name span_nb_v0 --model-version 0.1
python scripts/train_span_tagger.py --dataset datasets/commands/human_verified_span_commands.jsonl --model-output outputs/model_artifacts/span_nb_v1.json --metrics-output outputs/evaluations/span_nb_v1_metrics.json --validation-output outputs/evaluations/span_nb_v1_validation_metrics.json --seed 17 --model-name span_nb_v1 --model-version 0.2 --use-transitions
```

Current span-tagger results on human-verified span labels:

- `span_nb_v0`: validation token accuracy 0.6774, validation entity F1 0.5455; test token accuracy 0.5789, test entity F1 0.3656.
- `span_nb_v1`: validation token accuracy 0.7527, validation entity F1 0.6154; test token accuracy 0.6228, test entity F1 0.4198.

These are honest early baselines, not solved slot extractors.

Export a Colab-ready Hugging Face token-classification dataset:

```powershell
python scripts/export_hf_token_dataset.py --dataset datasets/commands/human_verified_span_commands.jsonl --output-dir outputs/hf_token_dataset
```

Fine-tune the transformer baseline in Google Colab with a T4 GPU runtime. In Colab, select `Runtime > Change runtime type > T4 GPU`, then verify CUDA before training:

```python
import torch

assert torch.cuda.is_available(), "Select a Colab GPU runtime before training"
print(torch.cuda.get_device_name(0))
```

Then run:

```powershell
python scripts/train_hf_token_classifier.py --dataset-dir outputs/hf_token_dataset --pretrained-model distilbert-base-uncased --output-dir outputs/model_artifacts/hf_token_classifier_distilbert_colab_t4 --metrics-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_metrics.json --validation-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_validation_metrics.json --epochs 30 --learning-rate 0.00005 --batch-size 8 --seed 17 --required-device-substring T4
```

The script refuses to train without CUDA. Do not report a Hugging Face fine-tuning result as provenance-complete unless the raw metrics file records the runtime, model, seed, parameters, split, and package versions.

Completed Colab/T4 DistilBERT token-classifier run, July 2, 2026:

- Notebook: `notebooks/Notebook2_NLP_Colab_T4.ipynb`
- Runtime verified in Colab: `T4 (Python 3)`
- Runtime metadata recorded in `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_metrics.json`: CUDA enabled on `Tesla T4`; `torch` 2.11.0+cu128; `transformers` 5.12.1; `accelerate` 1.14.0; `datasets` 4.0.0.
- Validation entity F1: 0.7945
- Test entity F1: 0.5926
- Raw metrics copied back from Colab: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_metrics.json` and `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_validation_metrics.json`
- Record-level held-out predictions: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_predictions.json`
- Held-out BIO error analysis: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_error_analysis.json`
- Error profile: 9 of 10 test records contain at least one entity error; largest false-negative bucket is `target` with 4 missed entities, and largest false-positive buckets are `constraint` with 8 entities and `target` with 7 entities.

Reviewed-label Colab/T4 DistilBERT token-classifier retrain, July 4, 2026:

- Runtime verified in Colab: `T4 (Python 3)`
- Runtime metadata recorded in `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_metrics.json`: CUDA enabled on `Tesla T4`; `torch` 2.11.0+cu128; `transformers` 5.12.1; `accelerate` 1.14.0; `datasets` 4.0.0.
- Data: `outputs/hf_token_dataset`, regenerated after applying the reviewed span command subset.
- Validation entity F1: 0.7945
- Test entity F1: 0.6047
- Test token accuracy: 0.7281
- Raw metrics copied back from Colab: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_metrics.json` and `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_validation_metrics.json`
- Record-level held-out predictions: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_test_predictions.json`
- Held-out BIO error analysis: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_test_error_analysis.json`

This retrain improves the previous held-out test entity F1 from 0.5926 to 0.6047 on the same 10-record test split. It is still a small-data Week 2 baseline with substantial entity errors, not a solved intent extractor.

Plan the next targeted human span-data batch from the reviewed error analysis:

```powershell
python scripts/plan_week2_span_collection.py --span-dataset datasets/commands/human_verified_span_commands.jsonl --evaluation outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_test_predictions.json --error-analysis outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_test_error_analysis.json --json-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_collection_plan.json --markdown-output reports/week2_targeted_span_collection_plan.md
```

Current targeted collection plan: 35 new human-written, human-verified span records, focused on `target`, `constraint`, `count`, `action`, and `location` errors. The generated plan does not contain new command text or gold labels. Since it is derived from held-out test errors, use the targeted records for train/validation expansion and create a fresh held-out test set before making stronger model claims.

Create the blank collection packet:

```powershell
python scripts/create_week2_collection_packet.py --plan outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_collection_plan.json --jsonl-output reports/week2_targeted_span_collection_packet.jsonl --markdown-output reports/week2_targeted_span_collection_packet.md
```

The current packet has 35 blank slots: 27 train and 8 validation. It is a worksheet only; it does not contain collected command text or labels.

After training, run record-level transformer evaluation and BIO error analysis in the same Colab T4 runtime:

```powershell
python scripts/evaluate_hf_token_classifier.py --dataset-dir outputs/hf_token_dataset --model-dir outputs/model_artifacts/hf_token_classifier_distilbert_colab_t4 --split test --evaluation-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_predictions.json --error-analysis-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_error_analysis.json --required-device-substring T4
```

Build a prioritized human-review queue from held-out transformer errors:

```powershell
python scripts/build_span_review_queue.py --evaluation outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_predictions.json --output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_queue.jsonl --summary-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_summary.json --focus-field target --focus-field constraint
```

This queue is not corrected training data. It marks model predictions as `model_generated_not_gold` and points to records that need human review before labels are changed or reused for training.

Export the queued records into an editable command file and a review report:

```powershell
python scripts/export_span_review_commands.py --span-dataset datasets/commands/human_verified_span_commands.jsonl --review-queue outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_queue.jsonl --commands-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_commands.txt --report-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_report.md --source-command-dataset datasets/commands/human_written_commands_curated_v1.jsonl
```

Open the report and command file together. Edit the command file only after human review, then apply the reviewed subset back into the full span dataset:

```powershell
python scripts/apply_span_review_commands.py --base-dataset datasets/commands/human_verified_span_commands.jsonl --commands-file outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_commands.txt --output datasets/commands/human_verified_span_commands.jsonl --summary-output outputs/evaluations/human_verified_span_commands_summary.json --bio-output outputs/evaluations/human_verified_span_commands_bio.jsonl
```

Use `apply_span_review_commands.py` for review subsets so unreviewed records are preserved. `rebuild_span_dataset_from_commands.py` is for full command files that intentionally recreate the whole dataset.

Create and validate real Week 2 command data only when the records are actually collected:

```powershell
python scripts/collect_week2_sample.py --text "Send two drones north and inspect the crops." --wav "C:\path\to\your_recording.wav" --split train
python scripts/create_command_record.py --output datasets/commands/human_written_commands.jsonl --id human_cmd_001 --text "Send two drones north and inspect the crops." --split train --source human_written_collection_v1 --data-type human_written_command --action inspect --count 2 --location north --target crops
python scripts/validate_command_dataset.py --dataset datasets/commands/human_written_commands.jsonl --summary-output outputs/evaluations/human_written_commands_summary.json --require-splits train,validation,test
python scripts/validate_audio_manifest.py --manifest datasets/sample_audio/manifest.jsonl --dataset-root . --summary-output outputs/evaluations/audio_manifest_summary.json
python scripts/audit_week2_collection.py --commands datasets/commands/human_written_commands_draft.jsonl --audio-manifest datasets/sample_audio/manifest.jsonl --dataset-root . --output outputs/evaluations/week2_collection_audit.json
```

The first command is the easiest path: type the transcript and pass a WAV path. It writes draft intent labels from the deterministic parser, marked with the current parser version such as `deterministic_v1_draft`. Review those labels before using them as human-verified training or evaluation labels.

These commands are for real collection files. The repository currently includes command collection artifacts and an audio manifest, but those are not a final human-verified benchmark or a Whisper ASR evaluation.

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
