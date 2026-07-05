# Shepherd-AI

Shepherd-AI is a planned Python research prototype for natural-language multi-drone mission planning and coordination in software simulation.

Current status: this repository contains project source documents, typed-command intent baselines, supervised span extraction baselines, a Colab/T4 DistilBERT token-classifier workflow, and a speech-input scaffold with a Whisper transcription script. It is not an end-to-end prototype, does not control physical drones, and does not yet implement grounding, planning, scheduling, vision, safety validation, or integrated mission execution.

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
- `docs/week2_audio_split_policy.md`
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

Audio model evaluation is separate from text intent extraction. The repository has 10 self-recorded WAV command records under `datasets/sample_audio/`. A local-GPU Whisper ASR result has been recorded, but a Colab/T4 ASR result has not, because the WAV files are intentionally not tracked in the public GitHub repository.

## Speech Input Scaffold

Milestone 2 currently validates audio/transcript manifests, evaluates transcript text, and includes a GPU-oriented Whisper transcription script. A first raw Whisper ASR evaluation has been run on the local `NVIDIA GeForce GTX 1650 SUPER` GPU, not on Colab/T4.

Manifest records should point to WAV files under the dataset root and include transcript provenance fields. See `docs/milestone_2_speech_input.md`.

Run Whisper ASR in Colab or another documented GPU environment:

```powershell
python scripts/transcribe_audio_whisper.py --manifest datasets/sample_audio/manifest.jsonl --dataset-root . --predictions-output outputs/evaluations/whisper_base_audio_predictions.jsonl --evaluation-output outputs/evaluations/whisper_base_audio_evaluation.json --model base --device cuda --language en --required-device-substring T4
```

The script writes raw predicted transcripts separately from the WER/exact-match evaluation.

Recorded local-GPU Whisper `base` ASR run, July 4, 2026:

- Predictions: `outputs/evaluations/whisper_base_audio_predictions_local_gtx1650.jsonl`
- Evaluation: `outputs/evaluations/whisper_base_audio_evaluation_local_gtx1650.json`
- Error analysis: `outputs/evaluations/whisper_base_audio_error_analysis_local_gtx1650.json`
- Split summary: `outputs/evaluations/whisper_base_audio_split_summary_local_gtx1650.json`
- Intent impact: `outputs/evaluations/whisper_base_intent_impact_local_gtx1650.json`
- Intent accuracy: `outputs/evaluations/whisper_base_intent_accuracy_local_gtx1650.json`
- Span impact: `outputs/evaluations/whisper_base_span_impact_local_gtx1650.json`
- Device: `NVIDIA GeForce GTX 1650 SUPER`
- Flags: `--device cuda --language en --required-device-substring GTX --no-fp16`
- Exact-match accuracy: `0.9`
- Mean word error rate: `0.01`
- Observed normalized word substitution: `fifty -> 50`

The audio manifest now has a retrospective seed-17 split: 6 train, 2 validation, and 2 test records. The split-level summary shows validation and test WER `0.0` on two records each, while the single `fifty -> 50` substitution is in train. This is still not a final audio benchmark because the split was assigned after the first pooled ASR result existed.

The ASR-to-intent impact analysis compares intent outputs from human transcripts and Whisper transcripts. It is not intent accuracy because no gold audio-intent labels are used. Current result: the `fifty -> 50` ASR substitution changes the raw extracted `constraints` string for one record under both `deterministic_v1` and `trained_nb_human_curated_v2`, but the normalized semantic intent comparison and canonical altitude-constraint comparison treat the two constraints as equivalent.

The audio-linked intent accuracy analysis reuses matching labels from `datasets/commands/human_written_commands_curated_v1.jsonl`; it does not create new gold labels. Current result on the 10 audio transcripts: human transcripts score exact-record accuracy `1.0`, and Whisper transcripts score `0.9` because the raw constraint string differs for `fifty` versus `50`.

The ASR-to-span impact analysis reuses matching labels from `datasets/commands/human_verified_span_commands.jsonl` for human-transcript accuracy, then compares span tagger predictions on human transcripts versus Whisper transcripts. Current result on the 10 matched audio transcripts: human-transcript span entity F1 is `0.7324` with `span_nb_v1`; Whisper changes one raw predicted constraint entity because `fifty` becomes `50`, but number-normalized semantic span predictions are unchanged. This is not ASR span accuracy because no separate human gold spans exist for the Whisper transcript text.

The current parser, transcript utilities, and constraint normalizer are not trained models. The constraint normalizer currently canonicalizes simple altitude-limit phrases such as `below fifty meters` and `below 50 meters`; it is not safety validation. A serious Week 2 implementation needs labeled command data, split definitions, and a trained or fine-tuned intent extraction component, with deterministic baselines retained for comparison.

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

- `span_nb_v0`: validation token accuracy 0.6857, validation entity F1 0.4969; test token accuracy 0.6667, test entity F1 0.4646.
- `span_nb_v1`: validation token accuracy 0.7143, validation entity F1 0.5753; test token accuracy 0.7018, test entity F1 0.5870.

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

Applied follow-up span batch, July 4, 2026:

- Corrected command file: `reports/week2_followup_span_commands_corrected.txt`
- Added 35 `manual_week2_span_annotation_v2` records to `datasets/commands/human_verified_span_commands.jsonl`
- Current span dataset: 85 records, split as 57 train, 18 validation, 10 test
- Current Hugging Face token dataset: 85 records and 809 tokens

Completed expanded 85-record Colab/T4 DistilBERT retrain, July 4, 2026:

- Runtime verified in Colab: `T4 (Python 3)`
- Data: 85-record `outputs/hf_token_dataset`
- Validation entity F1: 0.8382
- Test entity F1: 0.7857
- Test entity precision: 0.7500
- Test entity recall: 0.8250
- Test token accuracy: 0.8246
- Record-level held-out errors: 6 of 10 records still have at least one token error
- Raw artifacts: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_*`
- Review files: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_span_review_*`

This is the strongest Week 2 text-command span result so far, but it is not an ASR result and not end-to-end mission performance.

Current Week 2 status summary:

```powershell
python scripts/summarize_week2_status.py --audio-evaluation outputs/evaluations/whisper_base_audio_evaluation_local_gtx1650.json --intent-accuracy outputs/evaluations/whisper_base_intent_accuracy_local_gtx1650.json --intent-impact outputs/evaluations/whisper_base_intent_impact_local_gtx1650.json --span-impact outputs/evaluations/whisper_base_span_impact_local_gtx1650.json --hf-token-metrics outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_metrics.json --hf-token-error-analysis outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_test_error_analysis.json --output-json outputs/evaluations/week2_status_summary.json --output-markdown reports/week2_status_summary.md
```

The generated report is `reports/week2_status_summary.md`, with machine-readable output in `outputs/evaluations/week2_status_summary.json`.

Performance-risk audit for interpreting the current high metrics:

```powershell
python scripts/audit_week2_performance_risks.py --commands datasets/commands/human_written_commands_curated_v1.jsonl --spans datasets/commands/human_verified_span_commands.jsonl --audio-manifest datasets/sample_audio/manifest.jsonl --dataset-root . --status-summary outputs/evaluations/week2_status_summary.json --intent-model outputs/model_artifacts/intent_nb_human_curated_v2.json --output-json outputs/evaluations/week2_performance_risk_audit.json --output-markdown reports/week2_performance_risk_audit.md
```

The audit is `reports/week2_performance_risk_audit.md`, with machine-readable output in `outputs/evaluations/week2_performance_risk_audit.json`.

Pre-register a fresh non-overlapping audio batch before the next ASR run:

```powershell
python scripts/create_week2_audio_generalization_packet.py --commands datasets/commands/human_written_commands_curated_v1.jsonl --spans datasets/commands/human_verified_span_commands.jsonl --existing-audio-manifest datasets/sample_audio/manifest.jsonl --dataset-root . --jsonl-output reports/week2_audio_generalization_packet.jsonl --markdown-output reports/week2_audio_generalization_packet.md --validation-count 10 --test-count 20 --record-prefix audio_generalization
```

After real WAVs and human-verified transcripts are collected into a candidate manifest, audit it for overlap before ASR:

```powershell
python scripts/audit_week2_audio_generalization_manifest.py --candidate-manifest datasets/sample_audio/audio_generalization_manifest.jsonl --commands datasets/commands/human_written_commands_curated_v1.jsonl --spans datasets/commands/human_verified_span_commands.jsonl --existing-audio-manifest datasets/sample_audio/manifest.jsonl --dataset-root . --output outputs/evaluations/week2_audio_generalization_manifest_audit.json --fail-on-overlap
```

The current blank packet is `reports/week2_audio_generalization_packet.md` and `reports/week2_audio_generalization_packet.jsonl`. It contains no collected data or evaluation result.

Completed local-GPU Whisper run on the non-overlapping 30-record audio generalization batch:

- Manifest: `datasets/sample_audio/audio_generalization_manifest.jsonl`
- Report: `reports/week2_audio_generalization_asr_report.md`
- Exact transcript accuracy: `0.60`
- Mean word error rate: `0.0716`
- Downstream semantic intent changes: 7 of 30 records
- Important caveat: this is local GTX, not Colab/T4, and it is ASR-to-intent impact rather than gold intent accuracy.

Create draft intent labels for human review before reporting gold intent accuracy on the new audio batch:

```powershell
python scripts/create_week2_audio_intent_review_packet.py --manifest datasets/sample_audio/audio_generalization_manifest.jsonl --dataset-root . --jsonl-output reports/week2_audio_generalization_intent_review_packet.jsonl --markdown-output reports/week2_audio_generalization_intent_review_packet.md
```

The current review packet is `reports/week2_audio_generalization_intent_review_packet.md`. It has 30 draft labels, all marked `needs_human_review`; do not use them for training or accuracy reporting until corrected and marked as reviewed.

Export the draft packet into a compact editable review file:

```powershell
python scripts/export_audio_intent_review_commands.py --packet reports/week2_audio_generalization_intent_review_packet.jsonl --commands-output reports/week2_audio_generalization_intent_review_commands.jsonl --report-output reports/week2_audio_generalization_intent_review_commands.md
```

Open `reports/week2_audio_generalization_intent_review_commands.md` beside `reports/week2_audio_generalization_intent_review_commands.jsonl`. For each JSONL line, correct only the intent fields after human review of the transcript: `action`, `count`, `location`, `target`, and `constraints`. When a line has been reviewed, set `review_status` to `human_reviewed`, `data_type` to `human_verified_audio_intent_command`, and `label_source` to `human_reviewed_v1`.

Apply the reviewed compact file back into a full gold-label candidate:

```powershell
python scripts/apply_audio_intent_review_commands.py --packet reports/week2_audio_generalization_intent_review_packet.jsonl --commands-file reports/week2_audio_generalization_intent_review_commands.jsonl --output datasets/commands/audio_generalization_human_verified_intents.jsonl --summary-output outputs/evaluations/audio_generalization_human_verified_intents_summary.json --require-reviewed
```

This command should fail until every record has actually been marked as human-reviewed.

Validate review readiness before using any audio-intent JSONL as gold labels:

```powershell
python scripts/validate_audio_intent_review_packet.py --packet reports/week2_audio_generalization_intent_review_packet.jsonl --summary-output outputs/evaluations/week2_audio_generalization_intent_review_packet_summary.json --require-reviewed
```

The current draft packet intentionally fails `--require-reviewed`. After applying a fully reviewed compact file, validate `datasets/commands/audio_generalization_human_verified_intents.jsonl` instead.

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
