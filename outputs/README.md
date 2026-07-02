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
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_validation_metrics.json`: held-out validation/test metrics from a Colab T4 DistilBERT token-classification run on the human-verified span dataset.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_predictions.json`: planned record-level prediction output from `scripts/evaluate_hf_token_classifier.py`.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_error_analysis.json`: planned BIO false-positive/false-negative analysis from the same evaluator.

Generated Hugging Face checkpoint/model directories under `outputs/model_artifacts/hf_token_classifier*/` are ignored and should not be committed. Preserve small raw metrics JSON files for provenance, and record whether a run was Colab/T4 or exploratory local output.
