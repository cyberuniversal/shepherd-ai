# Outputs

Use this directory for raw experimental outputs and generated artifacts.

Rules:

- Keep raw outputs separate from analysis.
- Preserve failed and negative runs when they inform research decisions.
- Record model names, versions, parameters, dataset splits, and random seeds.
- Do not commit large model weights, private data, or undocumented generated artifacts.

Current Week 2 artifacts:

- `outputs/model_artifacts/intent_nb_v0.json`: preserved weak supervised baseline.
- `outputs/model_artifacts/intent_nb_v1.json`: improved supervised baseline with bigrams and schema-alias features.
- `outputs/evaluations/intent_nb_v0_metrics.json`
- `outputs/evaluations/intent_nb_v0_validation_metrics.json`
- `outputs/evaluations/intent_nb_v0_vs_deterministic.json`
- `outputs/evaluations/intent_nb_v1_metrics.json`
- `outputs/evaluations/intent_nb_v1_validation_metrics.json`
- `outputs/evaluations/intent_nb_v1_vs_deterministic.json`
- `outputs/model_artifacts/intent_nb_human_curated_v1.json`: trained on curated manual Week 2 commands.
- `outputs/evaluations/intent_nb_human_curated_v1_metrics.json`
- `outputs/evaluations/intent_nb_human_curated_v1_validation_metrics.json`
- `outputs/evaluations/intent_nb_human_curated_v1_vs_deterministic.json`
- `outputs/model_artifacts/intent_nb_human_curated_v2.json`: hybrid parser-gated baseline trained on curated manual Week 2 commands with rule overrides enabled.
- `outputs/evaluations/intent_nb_human_curated_v2_metrics.json`
- `outputs/evaluations/intent_nb_human_curated_v2_validation_metrics.json`
- `outputs/evaluations/intent_nb_human_curated_v2_vs_deterministic.json`
- `outputs/evaluations/human_written_commands_curated_v1_summary.json`
- `outputs/evaluations/human_written_commands_curated_v1_audit.json`
- `outputs/model_artifacts/span_nb_v0.json`: dependency-free supervised BIO span tagger baseline trained on human-verified span labels.
- `outputs/evaluations/span_nb_v0_validation_metrics.json`
- `outputs/evaluations/span_nb_v0_metrics.json`
- `outputs/evaluations/span_nb_v0_validation_error_analysis.json`
- `outputs/evaluations/span_nb_v0_error_analysis.json`
- `outputs/model_artifacts/span_nb_v1.json`: transition-aware supervised BIO span tagger baseline.
- `outputs/evaluations/span_nb_v1_validation_metrics.json`
- `outputs/evaluations/span_nb_v1_metrics.json`
- `outputs/evaluations/span_nb_v1_validation_error_analysis.json`
- `outputs/evaluations/span_nb_v1_error_analysis.json`
- `outputs/evaluations/span_nb_v0_v1_comparison.json`
- `outputs/evaluations/human_verified_span_commands_summary.json`
- `outputs/evaluations/human_verified_span_commands_bio.jsonl`
- `outputs/hf_token_dataset/`: Hugging Face token-classification JSONL export for Colab transformer fine-tuning.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_metrics.json`: test metrics and runtime/package metadata from a Colab T4 DistilBERT token-classification run on the human-verified span dataset.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_validation_metrics.json`: validation metrics from the same Colab T4 run.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_predictions.json`: record-level held-out predictions from `scripts/evaluate_hf_token_classifier.py`.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_error_analysis.json`: held-out BIO false-positive/false-negative analysis from the same evaluator.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_queue.jsonl`: prioritized human-review queue derived from held-out token-classifier errors.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_summary.json`: metadata and summary counts for that review queue.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_commands.txt`: editable command file generated from current gold spans for queued records.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_report.md`: human-readable context for reviewing those commands.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_metrics.json`: test metrics and runtime/package metadata from the reviewed-label Colab T4 DistilBERT retrain.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_validation_metrics.json`: validation metrics from the same reviewed-label Colab T4 retrain.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_test_predictions.json`: record-level held-out predictions from the reviewed-label retrain.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_test_error_analysis.json`: held-out BIO false-positive/false-negative analysis from the reviewed-label retrain.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_collection_plan.json`: machine-readable targeted human span-data collection plan derived from the reviewed-label retrain errors.

When applying reviewed command subsets, use `scripts/apply_span_review_commands.py` so unreviewed records are preserved. Do not use a subset command file as the only input to `scripts/rebuild_span_dataset_from_commands.py` unless replacing the whole dataset is intentional.

Generated Hugging Face checkpoint/model directories under `outputs/model_artifacts/hf_token_classifier*/` are ignored and should not be committed. Preserve small raw metrics JSON files for provenance, and record whether a run was Colab/T4 or exploratory local output.

Collection worksheets under `reports/`, such as `reports/week2_targeted_span_collection_packet.jsonl`, are not datasets. They may contain blank slots and collection guidance, but they must not be used for training until real command text and human-verified spans are added to a validated dataset file.
