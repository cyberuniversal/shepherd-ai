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
- Current `outputs/hf_token_dataset/` export: 85 records, split as 57 train, 18 validation, 10 test, generated after applying the 35-record `manual_week2_span_annotation_v2` follow-up batch.
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
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_metrics.json`: test metrics and runtime/package metadata from the expanded 85-record Colab T4 DistilBERT retrain.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_validation_metrics.json`: validation metrics from the expanded 85-record Colab T4 retrain.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_test_predictions.json`: record-level held-out predictions from the expanded 85-record Colab T4 retrain.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_test_error_analysis.json`: held-out BIO false-positive/false-negative analysis from the expanded 85-record Colab T4 retrain.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_span_review_queue.jsonl`: prioritized human-review queue derived from remaining expanded85 held-out errors.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_span_review_summary.json`: metadata and summary counts for that expanded85 review queue.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_span_review_commands.txt`: editable command file generated from current gold spans for the expanded85 queued records.
- `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_span_review_report.md`: human-readable context for reviewing the expanded85 queued records.
- `outputs/evaluations/audio_manifest_summary.json`: validation summary for the current 10-record human-recorded audio manifest.
- `outputs/evaluations/whisper_base_audio_predictions_local_gtx1650.jsonl`: raw Whisper `base` predictions from the local `NVIDIA GeForce GTX 1650 SUPER` GPU run.
- `outputs/evaluations/whisper_base_audio_evaluation_local_gtx1650.json`: transcript exact-match and WER evaluation for that same local-GPU ASR run.
- `outputs/evaluations/whisper_base_audio_error_analysis_local_gtx1650.json`: word-level error analysis for that same local-GPU ASR run.
- `outputs/evaluations/whisper_base_audio_split_summary_local_gtx1650.json`: train/validation/test ASR metrics for the retrospective seed-17 audio split.
- `outputs/evaluations/whisper_base_intent_impact_local_gtx1650.json`: comparison of downstream intent outputs on human transcripts versus Whisper transcripts.

Generate the ASR error analysis with:

```powershell
python scripts/analyze_asr_errors.py --evaluation outputs/evaluations/whisper_base_audio_evaluation_local_gtx1650.json --output outputs/evaluations/whisper_base_audio_error_analysis_local_gtx1650.json
```

Generate the ASR split summary with:

```powershell
python scripts/summarize_asr_by_split.py --manifest datasets/sample_audio/manifest.jsonl --dataset-root . --evaluation outputs/evaluations/whisper_base_audio_evaluation_local_gtx1650.json --output outputs/evaluations/whisper_base_audio_split_summary_local_gtx1650.json --split-policy "retrospective_seed17_6_2_2"
```

Generate the ASR-to-intent impact analysis with:

```powershell
python scripts/analyze_asr_intent_impact.py --manifest datasets/sample_audio/manifest.jsonl --dataset-root . --predictions outputs/evaluations/whisper_base_audio_predictions_local_gtx1650.jsonl --model outputs/model_artifacts/intent_nb_human_curated_v2.json --output outputs/evaluations/whisper_base_intent_impact_local_gtx1650.json
```

When applying reviewed command subsets, use `scripts/apply_span_review_commands.py` so unreviewed records are preserved. Do not use a subset command file as the only input to `scripts/rebuild_span_dataset_from_commands.py` unless replacing the whole dataset is intentional.

Generated Hugging Face checkpoint/model directories under `outputs/model_artifacts/hf_token_classifier*/` are ignored and should not be committed. Preserve small raw metrics JSON files for provenance, and record whether a run was Colab/T4 or exploratory local output.

Collection worksheets under `reports/`, such as `reports/week2_targeted_span_collection_packet.jsonl`, are not datasets. They may contain blank slots and collection guidance, but they must not be used for training until real command text and human-verified spans are added to a validated dataset file.
