# Week 2 Intent Training

## Scope

This document covers the first literature-driven Week 2 training pass: supervised text-command intent extraction.

The roadmap identifies Week 2 as speech recognition and intent extraction. The literature review indicates that a hand-written parser is only a baseline. A serious implementation needs labeled data, held-out evaluation, structured outputs, and comparison against baselines.

## Implemented

- Synthetic labeled command dataset: `datasets/commands/intent_labeled_synthetic.jsonl`.
- Split-aware dataset loader and validator.
- Trainable field-level multinomial Naive Bayes model for `action`, `location`, and `target`.
- Configurable feature extraction for unigrams, bigrams, and bounded schema-alias features.
- Rule-based count and constraint extraction reused from the deterministic parser.
- Deterministic parser `deterministic_v1`, which adds an open-vocabulary target phrase fallback after bounded aliases fail.
- Held-out test evaluation.
- Comparison against deterministic parser baselines.
- Field-level error analysis.
- Dataset split, provenance, data-type, and label summaries in training metadata.
- Saved-model evaluation on selected splits with `scripts/evaluate_intent_model.py`.
- Span-annotation validation and BIO export utilities.
- Trainable BIO span tagger baseline `span_nb_v0` for token-level slot extraction.
- Raw metrics under `outputs/evaluations/`.
- Lightweight JSON model artifact under `outputs/model_artifacts/`.

## Dataset

Synthetic dataset: `intent_labeled_synthetic.jsonl`

Split:

- Train: 18 records
- Validation: 4 records
- Test: 4 records

All records are labeled as `synthetic_literature_guided` and `synthetic_command`. This dataset is useful for developing the training workflow and checking leakage rules. It is not evidence of real user performance or speech performance.

Curated user-command dataset: `human_written_commands_curated_v1.jsonl`

Split:

- Train: 30 records
- Validation: 10 records
- Test: 10 records

These records came from the manual Week 2 collection pass and were curated from the draft labels into `data_type: human_written_command_assistant_labeled`. They are not audio-derived ASR results, and they are not a final human-verified benchmark.

Human-verified span dataset: `human_verified_span_commands.jsonl`

Split:

- Train: 30 records
- Validation: 10 records
- Test: 10 records

These records add exact character spans for token-level slot extraction. They are human-verified text-command span labels, not ASR-derived labels.

## Current Deterministic Baseline

`deterministic_v1` keeps the bounded JSON intent fields from `deterministic_v0` but reduces target-dictionary brittleness. When no target alias matches, it extracts a short target phrase for supported Week 2 actions such as `inspect`, `scan`, `capture`, and `search`.

Examples now covered without adding target aliases:

- `Send the nearest drone to inspect the livestock pen.`
- `Capture images of the red pickup truck.`
- `Scan the loading dock without crossing the road.`

This is still a deterministic baseline, not a trained model and not a final solution. The literature review supports deterministic validation, but not parser coverage as the entire language-understanding strategy. The fallback exists to make the baseline less fragile while preserving the structured-output contract needed by later grounding, planning, scheduling, and safety modules.

## Span Annotation Foundation

`docs/week2_span_annotation.md` defines a span-labeled dataset schema. `scripts/validate_span_dataset.py` validates exact character spans and can export BIO token labels for later spaCy or Hugging Face token-classification experiments.

The first trainable span baseline is `span_nb_v0`, a dependency-free Naive Bayes BIO tagger. It is a real supervised baseline over human-verified spans, but it is intentionally simple and not a final slot extractor.

## Baseline Command

```powershell
python scripts/train_intent_model.py `
  --dataset datasets/commands/intent_labeled_synthetic.jsonl `
  --model-output outputs/model_artifacts/intent_nb_v0.json `
  --metrics-output outputs/evaluations/intent_nb_v0_metrics.json `
  --comparison-output outputs/evaluations/intent_nb_v0_vs_deterministic.json `
  --validation-output outputs/evaluations/intent_nb_v0_validation_metrics.json `
  --seed 17
```

## Improved Command

```powershell
python scripts/train_intent_model.py `
  --dataset datasets/commands/intent_labeled_synthetic.jsonl `
  --model-output outputs/model_artifacts/intent_nb_v1.json `
  --metrics-output outputs/evaluations/intent_nb_v1_metrics.json `
  --comparison-output outputs/evaluations/intent_nb_v1_vs_deterministic.json `
  --validation-output outputs/evaluations/intent_nb_v1_validation_metrics.json `
  --seed 17 `
  --model-name trained_nb_v1 `
  --model-version 0.2 `
  --include-bigrams `
  --include-alias-features `
  --alias-feature-weight 3
```

## Saved-Model Evaluation Command

Use this when evaluating a frozen model on a validation, test, human-written, or gold-transcript dataset without retraining:

```powershell
python scripts/evaluate_intent_model.py `
  --model outputs/model_artifacts/intent_nb_v1.json `
  --dataset datasets/commands/intent_labeled_synthetic.jsonl `
  --split validation `
  --output outputs/evaluations/intent_nb_v1_saved_model_validation.json
```

## Curated User-Command Training Command

```powershell
python scripts/train_intent_model.py `
  --dataset datasets/commands/human_written_commands_curated_v1.jsonl `
  --model-output outputs/model_artifacts/intent_nb_human_curated_v1.json `
  --metrics-output outputs/evaluations/intent_nb_human_curated_v1_metrics.json `
  --comparison-output outputs/evaluations/intent_nb_human_curated_v1_vs_deterministic.json `
  --validation-output outputs/evaluations/intent_nb_human_curated_v1_validation_metrics.json `
  --seed 17 `
  --model-name trained_nb_human_curated_v1 `
  --model-version 0.1 `
  --include-bigrams `
  --include-alias-features `
  --alias-feature-weight 3
```

Hybrid parser-gated command:

```powershell
python scripts/train_intent_model.py `
  --dataset datasets/commands/human_written_commands_curated_v1.jsonl `
  --model-output outputs/model_artifacts/intent_nb_human_curated_v2.json `
  --metrics-output outputs/evaluations/intent_nb_human_curated_v2_metrics.json `
  --comparison-output outputs/evaluations/intent_nb_human_curated_v2_vs_deterministic.json `
  --validation-output outputs/evaluations/intent_nb_human_curated_v2_validation_metrics.json `
  --seed 17 `
  --model-name trained_nb_human_curated_v2 `
  --model-version 0.2 `
  --include-bigrams `
  --include-alias-features `
  --alias-feature-weight 3 `
  --use-rule-overrides
```

## Span Tagger Training Commands

Independent-token baseline:

```powershell
python scripts/train_span_tagger.py `
  --dataset datasets/commands/human_verified_span_commands.jsonl `
  --model-output outputs/model_artifacts/span_nb_v0.json `
  --metrics-output outputs/evaluations/span_nb_v0_metrics.json `
  --validation-output outputs/evaluations/span_nb_v0_validation_metrics.json `
  --seed 17 `
  --model-name span_nb_v0 `
  --model-version 0.1
```

Transition-aware baseline:

```powershell
python scripts/train_span_tagger.py `
  --dataset datasets/commands/human_verified_span_commands.jsonl `
  --model-output outputs/model_artifacts/span_nb_v1.json `
  --metrics-output outputs/evaluations/span_nb_v1_metrics.json `
  --validation-output outputs/evaluations/span_nb_v1_validation_metrics.json `
  --seed 17 `
  --model-name span_nb_v1 `
  --model-version 0.2 `
  --use-transitions
```

Compare saved span-tagger runs:

```powershell
python scripts/compare_span_tagger_runs.py `
  --metrics outputs/evaluations/span_nb_v0_metrics.json `
  --metrics outputs/evaluations/span_nb_v1_metrics.json `
  --output outputs/evaluations/span_nb_v0_v1_comparison.json
```

## Hugging Face Token Classifier Path

Export the human-verified spans into Hugging Face token-classification JSONL:

```powershell
python scripts/export_hf_token_dataset.py `
  --dataset datasets/commands/human_verified_span_commands.jsonl `
  --output-dir outputs/hf_token_dataset
```

The export writes `train.jsonl`, `validation.jsonl`, `test.jsonl`, `label_map.json`, and `dataset_summary.json`.

Fine-tuning should run in Google Colab with a T4 GPU runtime, not on local CPU. Select `Runtime > Change runtime type > T4 GPU`, install `transformers`, `torch`, `accelerate`, `datasets`, and `seqeval`, and verify CUDA before training:

```python
import torch

assert torch.cuda.is_available(), "Select a Colab GPU runtime before training"
print(torch.cuda.get_device_name(0))
```

Then run:

```powershell
python scripts/train_hf_token_classifier.py `
  --dataset-dir outputs/hf_token_dataset `
  --pretrained-model distilbert-base-uncased `
  --output-dir outputs/model_artifacts/hf_token_classifier_distilbert `
  --metrics-output outputs/evaluations/hf_token_classifier_distilbert_metrics.json `
  --validation-output outputs/evaluations/hf_token_classifier_distilbert_validation_metrics.json `
  --epochs 5 `
  --learning-rate 0.00002 `
  --batch-size 8 `
  --seed 17 `
  --required-device-substring T4
```

The script refuses to train without CUDA and records runtime/package metadata in the metrics output. Hugging Face model checkpoints are generated artifacts and should not be committed.

Completed Colab/T4 run, July 2, 2026:

- Notebook: `notebooks/Notebook2_NLP_Colab_T4.ipynb`
- Runtime: Google Colab `T4 (Python 3)` shown in the Colab status bar.
- Model: `distilbert-base-uncased`
- Data: `outputs/hf_token_dataset`, exported from `datasets/commands/human_verified_span_commands.jsonl`
- Seed: 17
- Epochs: 30
- Learning rate: 0.00005
- Batch size: 8
- Runtime/package metadata copied back from Colab in `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_metrics.json`: CUDA enabled on `Tesla T4`; `torch` 2.11.0+cu128; `transformers` 5.12.1; `accelerate` 1.14.0; `datasets` 4.0.0.
- Raw held-out metrics copied back from Colab: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_metrics.json` and `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_validation_metrics.json`.
- Record-level held-out predictions copied back from Colab: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_predictions.json`.
- Held-out BIO error analysis copied back from Colab: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_error_analysis.json`.

After training, run record-level evaluation and error analysis in the same Colab T4 runtime:

```powershell
python scripts/evaluate_hf_token_classifier.py `
  --dataset-dir outputs/hf_token_dataset `
  --model-dir outputs/model_artifacts/hf_token_classifier_distilbert_colab_t4 `
  --split test `
  --evaluation-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_predictions.json `
  --error-analysis-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_error_analysis.json `
  --required-device-substring T4
```

Build a prioritized review queue from the held-out prediction errors:

```powershell
python scripts/build_span_review_queue.py `
  --evaluation outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_predictions.json `
  --output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_queue.jsonl `
  --summary-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_summary.json `
  --focus-field target `
  --focus-field constraint
```

This review queue does not create new gold labels. It ranks records for human review using expected-versus-predicted BIO/entity disagreements and explicitly marks predictions as `model_generated_not_gold`.

Export editable review commands and a Markdown report:

```powershell
python scripts/export_span_review_commands.py `
  --span-dataset datasets/commands/human_verified_span_commands.jsonl `
  --review-queue outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_queue.jsonl `
  --commands-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_commands.txt `
  --report-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_report.md `
  --source-command-dataset datasets/commands/human_written_commands_curated_v1.jsonl
```

## Results

Held-out synthetic test result for `trained_nb_v0`:

- Field accuracy: 0.85
- Exact-record accuracy: 0.25
- Field error counts: `location`: 3

Validation result for `trained_nb_v0`:

- Field accuracy: 0.95
- Exact-record accuracy: 0.75
- Field error counts: `location`: 1

Held-out synthetic test result for `trained_nb_v1`:

- Field accuracy: 1.0
- Exact-record accuracy: 1.0
- Field error counts: none

Validation result for `trained_nb_v1`:

- Field accuracy: 1.0
- Exact-record accuracy: 1.0
- Field error counts: none

Comparison on the same synthetic test records:

- `deterministic_v0`: field accuracy 1.0, exact-record accuracy 1.0
- `trained_nb_v0`: field accuracy 0.85, exact-record accuracy 0.25
- `trained_nb_v1`: field accuracy 1.0, exact-record accuracy 1.0

Interpretation: `trained_nb_v0` is weaker than the deterministic parser on this tiny synthetic test set because its failures are concentrated in the `location` field. That negative/early result is preserved in `outputs/evaluations/intent_nb_v0_metrics.json`.

`trained_nb_v1` fixes those failures by adding bigrams and field-specific schema-alias features such as bounded action, location, and target aliases. This result is only a successful synthetic workflow check. It is not evidence that Shepherd-AI has solved real intent extraction, speech understanding, ambiguous command handling, grounding, planning, scheduling, or safety.

Curated user-command result for `trained_nb_human_curated_v1`:

- Validation field accuracy: 0.78
- Validation exact-record accuracy: 0.1
- Test field accuracy: 0.70
- Test exact-record accuracy: 0.2

Comparison on the curated user-command test split:

- `deterministic_v0`: field accuracy 1.0, exact-record accuracy 1.0
- `trained_nb_human_curated_v1`: field accuracy 0.70, exact-record accuracy 0.2

`trained_nb_human_curated_v1` remains a useful negative result: the trained field classifier still cannot predict unseen or rare targets and actions reliably.

Curated user-command result for `trained_nb_human_curated_v2`:

- Validation field accuracy: 1.0
- Validation exact-record accuracy: 1.0
- Test field accuracy: 1.0
- Test exact-record accuracy: 1.0

Interpretation: `trained_nb_human_curated_v2` is a hybrid parser-gated baseline. It uses the Naive Bayes training artifact but makes bounded deterministic parser outputs authoritative for `action`, `location`, and `target`. This is not evidence that a pure trained model solved the broader command set. It shows that the literature-supported pattern of bounded structured parsing plus deterministic validation is currently stronger for this small dataset than the field-level Naive Bayes classifier alone.

Historical result note: the raw results above were generated before the open-vocabulary fallback and are labeled `deterministic_v0` where applicable. New parser outputs and new comparison artifacts should be labeled `deterministic_v1`.

Span tagger result for `span_nb_v0`:

- Validation token accuracy: 0.6774
- Validation entity F1: 0.5455
- Test token accuracy: 0.5789
- Test entity F1: 0.3656

Interpretation: `span_nb_v0` is a useful negative/early baseline. It confirms that the span-label pipeline, BIO conversion, training, and held-out evaluation work, but the model is not strong enough to treat as solved slot extraction. The low held-out entity F1 supports moving next to a stronger sequence model, more data, or both.

Span tagger result for `span_nb_v1`:

- Validation token accuracy: 0.7527
- Validation entity F1: 0.6154
- Test token accuracy: 0.6228
- Test entity F1: 0.4198

Interpretation: `span_nb_v1` adds transition-aware Viterbi decoding. The test entity F1 improves over `span_nb_v0` from 0.3656 to 0.4198. The error analysis shows the improvement mostly comes from fewer false-positive entities, not from finding more true entities. This is still not strong enough to treat as solved slot extraction.

Colab/T4 Hugging Face token-classifier result for `hf_token_classifier_distilbert_colab_t4`:

- Validation entity F1: 0.7945
- Validation entity precision: 0.7632
- Validation entity recall: 0.8286
- Test entity F1: 0.5926
- Test entity precision: 0.5217
- Test entity recall: 0.6857
- Test token accuracy: 0.7368
- Test record-level error analysis: 9 of 10 records have at least one entity error; false negatives are highest for `target` with 4 missed entities, followed by `constraint`, `count`, and `location` with 2 each; false positives are highest for `constraint` with 8 entities and `target` with 7 entities.
- Review queue generated from held-out predictions: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_queue.jsonl`.
- Review queue summary: 9 records require review; focus-field record counts are `constraint`: 8 and `target`: 4.
- Editable review command file: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_commands.txt`.
- Human-readable review report: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_report.md`.

Interpretation: the DistilBERT token classifier is the first completed transformer baseline for Week 2 span extraction. It improves over the dependency-free `span_nb_v1` baseline on both validation entity F1 and held-out test entity F1, but it is still trained and evaluated on only 50 human-verified span records. The error profile shows remaining confusion between targets and constraints, so this is an encouraging baseline result, not evidence that slot extraction is solved.

## Not Implemented

- No final human-verified command benchmark.
- No ASR-derived intent dataset.
- No Whisper ASR evaluation.
- No spaCy fine-tuning result yet.
- No grounding, planning, scheduling, vision, safety validation, or end-to-end mission evaluation.

## Next Training Work

- Expand labeled commands with more paraphrases and edge cases.
- Convert assistant-curated command labels into a human-verified benchmark before using them as strong evidence.
- Evaluate deterministic parser and trained model by data type.
- Add a stronger spaCy or Hugging Face span/slot baseline once dataset size and environment setup justify it.
- Evaluate intent extraction separately on gold transcripts and ASR transcripts when audio exists.
