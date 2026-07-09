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
- Deterministic parser `deterministic_v2`, which extends the open-vocabulary fallback with post-hoc audio-batch error fixes.
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

- Train: 57 records
- Validation: 18 records
- Test: 10 records

These records add exact character spans for token-level slot extraction. They are human-verified text-command span labels, not ASR-derived labels. The dataset currently includes 50 records from `manual_week2_span_annotation_v1` and 35 targeted follow-up records from `manual_week2_span_annotation_v2`.

## Current Deterministic Baseline

`deterministic_v1` kept the bounded JSON intent fields from `deterministic_v0` but reduced target-dictionary brittleness. When no target alias matched, it extracted a short target phrase for supported Week 2 actions such as `inspect`, `scan`, `capture`, and `search`.

`deterministic_v2` is the current parser. It was created after inspecting the reviewed 30-record audio-generalization batch, so same-batch metrics are post-hoc rather than a clean final benchmark. It adds targeted handling for `scan/search/check X for Y`, map/monitor/photograph wording, open-vocabulary location phrases, compound-command constraints, and a small number of observed ASR confusions.

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

Reviewed-label Colab/T4 retrain, July 4, 2026:

- Notebook: `notebooks/Notebook2_NLP_Colab_T4.ipynb`
- Runtime: Google Colab `T4 (Python 3)`.
- Model: `distilbert-base-uncased`
- Data: `outputs/hf_token_dataset`, regenerated from `datasets/commands/human_verified_span_commands.jsonl` after the reviewed test split span commands were applied.
- Seed: 17
- Epochs: 30
- Learning rate: 0.00005
- Batch size: 8
- Runtime/package metadata copied back from Colab in `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_metrics.json`: CUDA enabled on `Tesla T4`; `torch` 2.11.0+cu128; `transformers` 5.12.1; `accelerate` 1.14.0; `datasets` 4.0.0.
- Raw held-out metrics copied back from Colab: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_metrics.json` and `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_validation_metrics.json`.
- Record-level held-out predictions copied back from Colab: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_test_predictions.json`.
- Held-out BIO error analysis copied back from Colab: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_test_error_analysis.json`.

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

After human review, apply the edited subset without dropping unreviewed records:

```powershell
python scripts/apply_span_review_commands.py `
  --base-dataset datasets/commands/human_verified_span_commands.jsonl `
  --commands-file outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_commands.txt `
  --output datasets/commands/human_verified_span_commands.jsonl `
  --summary-output outputs/evaluations/human_verified_span_commands_summary.json `
  --bio-output outputs/evaluations/human_verified_span_commands_bio.jsonl
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

Historical result note: the raw results above were generated before the current audio-oriented parser updates and may be labeled `deterministic_v0` or `deterministic_v1` where applicable. New parser outputs and new comparison artifacts should be labeled `deterministic_v2`.

Span tagger result for `span_nb_v0`:

- Validation token accuracy: 0.6857
- Validation entity F1: 0.4969
- Test token accuracy: 0.6667
- Test entity F1: 0.4646

Interpretation: `span_nb_v0` is a useful negative/early baseline. It confirms that the span-label pipeline, BIO conversion, training, and held-out evaluation work, but the model is not strong enough to treat as solved slot extraction. The expanded training data improved its held-out test score over the earlier 50-record run, but the result is still weak.

Span tagger result for `span_nb_v1`:

- Validation token accuracy: 0.7143
- Validation entity F1: 0.5753
- Test token accuracy: 0.7018
- Test entity F1: 0.5870

Interpretation: `span_nb_v1` adds transition-aware Viterbi decoding. On the expanded 85-record dataset, the test entity F1 improves over `span_nb_v0` from 0.4646 to 0.5870. This is still not strong enough to treat as solved slot extraction, but it confirms the new follow-up records improved the lightweight local baseline.

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

Interpretation: the DistilBERT token classifier is the first completed transformer baseline for Week 2 span extraction. It improves over the dependency-free `span_nb_v1` baseline on both validation entity F1 and held-out test entity F1, but it was trained and evaluated on only the first 50 human-verified span records. The error profile shows remaining confusion between targets and constraints, so this is an encouraging baseline result, not evidence that slot extraction is solved.

Reviewed-label Colab/T4 Hugging Face token-classifier result for `hf_token_classifier_distilbert_colab_t4_reviewed`:

- Validation entity F1: 0.7945
- Validation entity precision: 0.7632
- Validation entity recall: 0.8286
- Test entity F1: 0.6047
- Test entity precision: 0.5652
- Test entity recall: 0.6500
- Test token accuracy: 0.7281
- Test record-level error analysis: 8 of 10 records are listed in the worst-record queue; false negatives are highest for `action` and `target` with 4 missed entities each, followed by `constraint`, `count`, and `location` with 2 each; false positives are highest for `constraint` with 8 entities and `target` with 7 entities.

Interpretation: the reviewed-label retrain is a small held-out test improvement over the previous Colab/T4 transformer baseline, from test entity F1 0.5926 to 0.6047. Validation entity F1 is unchanged at 0.7945. This is a provenance-complete retrain on the reviewed 50-record span dataset, not evidence that slot extraction is solved. The model still has substantial entity-level errors.

## Targeted Collection Plan

Build the next human data collection batch from the reviewed Colab/T4 error analysis:

```powershell
python scripts/plan_week2_span_collection.py `
  --span-dataset datasets/commands/human_verified_span_commands.jsonl `
  --evaluation outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_test_predictions.json `
  --error-analysis outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_test_error_analysis.json `
  --json-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_collection_plan.json `
  --markdown-output reports/week2_targeted_span_collection_plan.md
```

Current plan output, generated from the reviewed run:

- Minimum next batch: 35 human-written, human-verified span records.
- Highest-priority fields: `target` with 11 requested records and `constraint` with 10 requested records.
- Additional requested coverage: `count` 6 records, `action` 5 records, and `location` 3 records.
- Split policy: put targeted follow-up records in train or validation only, because the plan is derived from held-out test errors. Do not treat targeted follow-up records as an unbiased test result.

This plan does not generate command text or gold labels. It only turns the current error profile into collection requirements. New command text must be human-written or explicitly labeled as synthetic/model-generated.

Create a blank collection packet from that plan:

```powershell
python scripts/create_week2_collection_packet.py `
  --plan outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_collection_plan.json `
  --jsonl-output reports/week2_targeted_span_collection_packet.jsonl `
  --markdown-output reports/week2_targeted_span_collection_packet.md
```

Current packet output:

- 35 blank collection slots.
- Recommended splits: 27 train, 8 validation, 0 test.
- Slot IDs: `human_cmd_followup_001` through `human_cmd_followup_035`.
- The packet is a worksheet, not a dataset. Every `text` field and `spans` list is blank until a human writes the command and verifies exact character spans.

Applied follow-up batch, July 4, 2026:

- Corrected command file: `reports/week2_followup_span_commands_corrected.txt`.
- Records added: 35.
- Source: `manual_week2_span_annotation_v2`.
- Updated span dataset: 85 records total, with 57 train, 18 validation, and the original 10-record test split unchanged.
- Updated span counts: `action`: 104, `constraint`: 20, `count`: 50, `location`: 39, `target`: 81.
- Updated Hugging Face token dataset: 85 records and 809 tokens.
- Important: the Colab/T4 transformer metrics above are now pre-expansion results. Retrain in Colab T4 before reporting a result for the 85-record dataset.

Expanded 85-record Colab/T4 retrain, July 4, 2026:

- Notebook: `notebooks/Notebook2_NLP_Colab_T4.ipynb`
- Runtime: Google Colab `T4 (Python 3)`.
- Model: `distilbert-base-uncased`
- Data: `outputs/hf_token_dataset`, exported from the 85-record `datasets/commands/human_verified_span_commands.jsonl`.
- Seed: 17
- Epochs: 30
- Learning rate: 0.00005
- Batch size: 8
- Runtime/package metadata copied back from Colab in `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_metrics.json`: CUDA enabled on `Tesla T4`; `torch` 2.11.0+cu128; `transformers` 5.12.1; `accelerate` 1.14.0; `datasets` 4.0.0.
- Validation entity F1: 0.8382
- Validation entity precision: 0.7917
- Validation entity recall: 0.8906
- Test entity F1: 0.7857
- Test entity precision: 0.7500
- Test entity recall: 0.8250
- Test token accuracy: 0.8246
- Test record-level error analysis: 6 of 10 records have at least one token error; false negatives are `target`: 2, `count`: 2, `action`: 1, `constraint`: 1, and `location`: 1; false positives are `target`: 4, `constraint`: 3, `count`: 2, `action`: 1, and `location`: 1.
- Raw artifacts copied back from Colab: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_metrics.json`, `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_validation_metrics.json`, `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_test_predictions.json`, and `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_test_error_analysis.json`.
- Review queue generated from remaining held-out errors: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_span_review_queue.jsonl`.
- Review queue summary: 6 records require review; focus-field record counts are `constraint`: 4 and `target`: 3.
- Editable review command file: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_span_review_commands.txt`.
- Human-readable review report: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_span_review_report.md`.

Interpretation: the expanded-dataset transformer retrain is the strongest Week 2 slot-extraction result so far. Held-out test entity F1 improved from 0.6047 to 0.7857 after adding the 35 targeted follow-up span records. This is still not a solved intent extractor: the held-out test split has only 10 records, the result is text-command-only, and ASR/Whisper performance is still not evaluated.

### Span-To-Intent Assembly

The roadmap requires intent JSON fields, not only BIO tags. To measure whether the trained span extractor can support that interface, run:

```powershell
python scripts/evaluate_span_intent_assembly.py `
  --evaluation outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_test_predictions.json `
  --output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_span_intent_assembly.json
```

Current result:

- Report: `reports/week2_span_intent_assembly_report.md`.
- Records: 10 held-out test commands.
- Exact assembled-intent accuracy: 5 / 10 = 0.5000.
- Field accuracy: 43 / 50 = 0.8600.
- Field errors: `constraints`: 4, `location`: 2, `target`: 1.
- Predicted intents with deterministic validation warnings: 4 / 10.
- Validation warnings: `missing_expected_location`: 3, `suspicious_short_constraint`: 1.
- Path comparison output: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_intent_path_comparison.json`.
- On the same span-derived benchmark, `deterministic_v3` scores 1 / 10 exact and 0.5800 field accuracy, `span_intent_assembly` scores 5 / 10 exact and 0.8600 field accuracy, and post-hoc `hybrid_span_parser` scores 10 / 10 exact and 1.0000 field accuracy.

Interpretation: the trained span model preserves much of the structure, but location, target, and constraint boundary errors still prevent reliable JSON intent assembly. The conservative hybrid shows why the training was useful: the trained route captures schema fields that the deterministic parser misses on this benchmark, while deterministic validation can filter or repair some bad model spans. Because the hybrid was developed after inspecting these same 10 span-test errors, the 10 / 10 result is development evidence only, not a clean final benchmark. This supports keeping deterministic validation between NLP output and later grounding/planning modules.

### ASR Span-To-Intent Impact

The local audio artifacts can also be used to measure whether Whisper transcript differences change span-assembled intent JSON:

```powershell
python scripts/analyze_asr_span_intent_impact.py `
  --span-impact outputs/evaluations/whisper_base_span_impact_local_gtx1650.json `
  --output outputs/evaluations/whisper_base_span_intent_impact_local_gtx1650.json
```

Current result on the 10-record local audio sample:

- Output: `outputs/evaluations/whisper_base_span_intent_impact_local_gtx1650.json`.
- `span_intent_assembly`: 1 / 10 intent changes from human transcript to Whisper transcript.
- `hybrid_span_parser`: 1 / 10 intent changes from human transcript to Whisper transcript.
- The changed record is `audio_006`, where the raw constraint changes from `keep them below fifty meters` to `keep them below 50 meters`.

Interpretation: this is ASR-to-span-intent impact analysis, not gold ASR intent accuracy. No human-verified span labels exist for the Whisper transcript text, so this measures whether model predictions change between transcript versions.

### Transformer Transcript Inference

The stronger Colab/T4 token classifier should also be run directly on transcript JSONL files after the checkpoint directory is restored in Colab:

```powershell
python scripts/predict_hf_token_classifier_transcripts.py `
  --input-jsonl outputs/evaluations/whisper_base_audio_predictions_local_gtx1650.jsonl `
  --model-dir outputs/model_artifacts/hf_token_classifier_distilbert_colab_t4_expanded85 `
  --transcript-field expected_transcript `
  --output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_human_transcript_predictions.json `
  --required-device-substring T4

python scripts/predict_hf_token_classifier_transcripts.py `
  --input-jsonl outputs/evaluations/whisper_base_audio_predictions_local_gtx1650.jsonl `
  --model-dir outputs/model_artifacts/hf_token_classifier_distilbert_colab_t4_expanded85 `
  --transcript-field predicted_transcript `
  --output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_asr_transcript_predictions.json `
  --required-device-substring T4
```

These commands produce model-generated spans, raw span-assembled intents, hybrid span-parser intents, and validation issues for each transcript. They do not produce accuracy by themselves. The Hugging Face checkpoint directory is generated output and is ignored by git, so this step must run in Colab after training or after restoring the checkpoint artifact.

Package the trained checkpoint before leaving Colab:

```powershell
python scripts/package_hf_checkpoint.py `
  --model-dir outputs/model_artifacts/hf_token_classifier_distilbert_colab_t4_expanded85 `
  --output-zip /content/hf_token_classifier_distilbert_colab_t4_expanded85.zip `
  --include outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_metrics.json `
  --include outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_validation_metrics.json `
  --include outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_test_predictions.json `
  --include outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_test_error_analysis.json
```

Download `/content/hf_token_classifier_distilbert_colab_t4_expanded85.zip` from the Colab Files pane or by running `files.download(...)` in the notebook packaging cell. The local notebook downloads in `D:\Users\momoa\Downloads` confirm the run and metrics, but they do not contain model weights.

After the zip is downloaded, import it locally:

```powershell
python scripts/import_hf_checkpoint.py `
  --checkpoint-zip D:\Users\momoa\Downloads\hf_token_classifier_distilbert_colab_t4_expanded85.zip `
  --output-dir outputs/model_artifacts `
  --expected-name hf_token_classifier_distilbert_colab_t4_expanded85 `
  --overwrite
```

The importer rejects notebook exports and incomplete archives. A valid zip must contain at least `config.json`, a supported weight file such as `model.safetensors`, and tokenizer files.

Imported checkpoint result, July 6, 2026:

- Downloaded checkpoint zip: `D:\Users\momoa\Downloads\hf_token_classifier_distilbert_colab_t4_expanded85.zip`.
- Local imported checkpoint directory: `outputs/model_artifacts/hf_token_classifier_distilbert_colab_t4_expanded85`.
- Imported files include `config.json`, `model.safetensors`, `tokenizer.json`, `tokenizer_config.json`, `training_args.bin`, `checkpoint_manifest.json`, and `local_import_manifest.json`.
- The checkpoint directory is ignored by git and must not be committed.
- Local inference used `.venv312` with `torch` 2.12.1+cu126, `transformers` 5.13.0, `accelerate` 1.14.0, and `datasets` 5.0.0 recorded via package metadata. This was inference only, not local training.

Evaluate the imported transformer on the 30-record `audio_v2_holdout` transcript benchmark:

```powershell
.\.venv312\Scripts\python.exe scripts\predict_hf_token_classifier_transcripts.py `
  --input-jsonl outputs\evaluations\whisper_base_audio_v2_holdout_predictions_local_gtx1650.jsonl `
  --model-dir outputs\model_artifacts\hf_token_classifier_distilbert_colab_t4_expanded85 `
  --transcript-field expected_transcript `
  --output outputs\evaluations\hf_token_classifier_distilbert_colab_t4_expanded85_audio_v2_holdout_human_transcript_predictions.json

.\.venv312\Scripts\python.exe scripts\predict_hf_token_classifier_transcripts.py `
  --input-jsonl outputs\evaluations\whisper_base_audio_v2_holdout_predictions_local_gtx1650.jsonl `
  --model-dir outputs\model_artifacts\hf_token_classifier_distilbert_colab_t4_expanded85 `
  --transcript-field predicted_transcript `
  --output outputs\evaluations\hf_token_classifier_distilbert_colab_t4_expanded85_audio_v2_holdout_asr_transcript_predictions.json

python scripts\evaluate_hf_transcript_intent_accuracy.py `
  --predictions outputs\evaluations\hf_token_classifier_distilbert_colab_t4_expanded85_audio_v2_holdout_human_transcript_predictions.json `
  --gold-commands datasets\commands\audio_v2_holdout_human_verified_intents.jsonl `
  --output outputs\evaluations\hf_token_classifier_distilbert_colab_t4_expanded85_audio_v2_holdout_human_transcript_intent_accuracy.json `
  --include-deterministic

python scripts\evaluate_hf_transcript_intent_accuracy.py `
  --predictions outputs\evaluations\hf_token_classifier_distilbert_colab_t4_expanded85_audio_v2_holdout_asr_transcript_predictions.json `
  --gold-commands datasets\commands\audio_v2_holdout_human_verified_intents.jsonl `
  --output outputs\evaluations\hf_token_classifier_distilbert_colab_t4_expanded85_audio_v2_holdout_asr_transcript_intent_accuracy.json `
  --include-deterministic
```

Current `audio_v2_holdout` transformer transcript-intent result:

- Report: `reports/week2_transformer_transcript_intent_report.md`.
- Error analysis: `reports/week2_transformer_transcript_intent_error_analysis.md`.
- Human/reference transcripts: `deterministic_v3` exact intent accuracy 30 / 30 = 1.0000; `hybrid_span_parser` 6 / 30 = 0.2000; `span_intent_assembly` 5 / 30 = 0.1667.
- ASR/Whisper transcripts: `deterministic_v3` exact intent accuracy 27 / 30 = 0.9000; `hybrid_span_parser` 5 / 30 = 0.1667; `span_intent_assembly` 4 / 30 = 0.1333.
- Interpretation: the imported transformer span model is not currently competitive with the deterministic parser for final intent JSON on the `audio_v2_holdout` benchmark. This is a useful negative result, not a failed training run. The model remains useful as a trainable span extractor, but the final intent assembly layer needs better supervision or design before it can replace the deterministic baseline.

Generate the paired failure analysis:

```powershell
python scripts\analyze_hf_transcript_intent_errors.py `
  --human-evaluation outputs\evaluations\hf_token_classifier_distilbert_colab_t4_expanded85_audio_v2_holdout_human_transcript_intent_accuracy.json `
  --asr-evaluation outputs\evaluations\hf_token_classifier_distilbert_colab_t4_expanded85_audio_v2_holdout_asr_transcript_intent_accuracy.json `
  --json-output outputs\evaluations\hf_token_classifier_distilbert_colab_t4_expanded85_audio_v2_holdout_transcript_intent_error_analysis.json `
  --markdown-output reports\week2_transformer_transcript_intent_error_analysis.md
```

Current paired failure analysis: `span_intent_assembly` has 25 human-transcript error records and 26 ASR-transcript error records; `hybrid_span_parser` has 24 human-transcript error records and 25 ASR-transcript error records. ASR adds only 1 extra failure for each transformer span path, while `deterministic_v3` has 0 human-transcript failures and 3 ASR-added failures. The immediate bottleneck is therefore the trained span-to-intent path itself, not Whisper.

Create a human span-labeling remediation packet from the clean-transcript failures:

```powershell
python scripts\create_audio_span_remediation_packet.py `
  --evaluation outputs\evaluations\hf_token_classifier_distilbert_colab_t4_expanded85_audio_v2_holdout_human_transcript_intent_accuracy.json `
  --gold-commands datasets\commands\audio_v2_holdout_human_verified_intents.jsonl `
  --system hybrid_span_parser `
  --jsonl-output reports\week2_audio_v2_span_remediation_packet.jsonl `
  --markdown-output reports\week2_audio_v2_span_remediation_packet.md `
  --source manual_week2_audio_v2_span_remediation_v1
```

Current remediation packet:

- Records needing human span review: 24.
- Split counts: validation 7, test 17.
- Failed field counts: `location`: 15, `target`: 11, `constraints`: 8, `action`: 5.
- Important: this packet has blank `spans` lists. It is a worksheet, not a dataset. If used for training or assembly tuning, these records should be marked as development data and not reused as a clean final benchmark.

## Not Implemented

- No final clean human-verified command benchmark.
- No final clean ASR-derived intent benchmark for the current post-hoc parser state.
- No Colab/T4 Whisper ASR evaluation.
- No clean post-`deterministic_v3` fresh audio benchmark; `audio_v2_holdout` is now a diagnostic/development benchmark with human-reviewed labels.
- No spaCy fine-tuning result yet.
- No grounding, planning, scheduling, vision, safety validation, or end-to-end mission evaluation.

## Next Training Work

- Expand labeled commands with more paraphrases and edge cases.
- Convert assistant-curated command labels into a human-verified benchmark before using them as strong evidence.
- Evaluate deterministic parser and trained model by data type.
- Add a stronger spaCy or Hugging Face span/slot baseline once dataset size and environment setup justify it.
- Evaluate intent extraction separately on gold transcripts and ASR transcripts when audio exists.
