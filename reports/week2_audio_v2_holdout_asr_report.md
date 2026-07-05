# Week 2 Audio V2 Holdout ASR Report

This report summarizes the fresh audio holdout collected after `deterministic_v2` was created. It is intended to test generalization beyond the reviewed audio batch that motivated the parser update.

## Batch

- Manifest: `datasets/sample_audio/audio_v2_holdout_manifest.jsonl`
- Records: 30
- Split: 10 validation, 20 test
- Source: `manual_week2_audio_v2_holdout_v1`
- Data type: `human_recorded_audio`
- Manifest summary: `outputs/evaluations/audio_v2_holdout_manifest_summary.json`
- Non-overlap audit: `outputs/evaluations/week2_audio_v2_holdout_manifest_audit.json`
- Audit result: 0 overlap records, 0 duplicate candidate transcripts

The overlap audit blocks prior curated commands, human-verified span commands, the original 10-record audio manifest, and the first 30-record audio-generalization manifest.

## ASR Run

- Model: Whisper `base`
- Runtime: local Windows GPU run, not Colab/T4
- Device: `NVIDIA GeForce GTX 1650 SUPER`
- Python: 3.12.10
- Torch: 2.12.1+cu126
- openai-whisper: 20250625
- Flags: `--device cuda --language en --required-device-substring GTX --no-fp16`

Artifacts:

- Raw predictions: `outputs/evaluations/whisper_base_audio_v2_holdout_predictions_local_gtx1650.jsonl`
- Transcript evaluation: `outputs/evaluations/whisper_base_audio_v2_holdout_evaluation_local_gtx1650.json`
- Error analysis: `outputs/evaluations/whisper_base_audio_v2_holdout_error_analysis_local_gtx1650.json`
- Split summary: `outputs/evaluations/whisper_base_audio_v2_holdout_split_summary_local_gtx1650.json`
- ASR-to-intent impact: `outputs/evaluations/whisper_base_audio_v2_holdout_intent_impact_local_gtx1650.json`

## ASR Metrics

- Overall exact transcript accuracy: 22 / 30 = 0.7333
- Overall mean word error rate: 0.0485
- Validation exact transcript accuracy: 6 / 10 = 0.6000
- Validation mean word error rate: 0.1016
- Test exact transcript accuracy: 16 / 20 = 0.8000
- Test mean word error rate: 0.0219

Word-level error analysis:

- Error records: 8
- Substitutions: 10
- Insertions: 3
- Deletions: 0

Observed substitutions include:

- `scan -> scam`
- `drone -> drawn`
- `courtyard -> and`
- `entrance -> trim`
- `gatehouse -> house`
- `eastern -> easter`
- `two -> 2`
- `four -> 4`
- `eight -> 8`

## ASR-To-Intent Impact

This is not gold intent accuracy. It compares `deterministic_v2` outputs on human transcripts versus Whisper transcripts.

For both `deterministic_v2` and the parser-gated `trained_nb_human_curated_v2`:

- Raw transcript changed records: 12 / 30
- Normalized word changed records: 8 / 30
- Raw intent changed records: 5 / 30
- Semantic intent changed records: 5 / 30
- Canonical constraint changed records: 0 / 30

Changed semantic fields:

- `target`: 5
- `location`: 3
- `count`: 1
- `action`: 1

## Intent Review Status

Draft intent labels have been generated but are not gold labels:

- Draft packet: `reports/week2_audio_v2_holdout_intent_review_packet.jsonl`
- Draft packet report: `reports/week2_audio_v2_holdout_intent_review_packet.md`
- Editable review file: `reports/week2_audio_v2_holdout_intent_review_commands.jsonl`
- Editable review report: `reports/week2_audio_v2_holdout_intent_review_commands.md`
- Review readiness summary: `outputs/evaluations/week2_audio_v2_holdout_intent_review_packet_summary.json`

Current readiness:

- Records: 30
- Draft records: 30
- Not reviewed records: 30
- Ready for gold evaluation: false

Do not report intent accuracy on this holdout until the intent labels are human-reviewed and applied with `scripts/apply_audio_intent_review_commands.py`.

## Interpretation

The fresh holdout improves on the previous non-overlapping ASR exact transcript result: 0.7333 here versus 0.6000 on the first 30-record audio-generalization batch. The test split is stronger than the validation split in this run, but both remain small.

`deterministic_v2` appears less sensitive to ASR noise than the earlier parser on this batch: only 5 of 30 records change semantic intent between human and Whisper transcripts. The remaining ASR-induced semantic changes still affect mission-critical fields, especially `target` and `location`.

## Current Limitations

- This is a local GTX run, not a Colab/T4 run.
- The audio files are untracked; only manifests and outputs are documented.
- Intent labels are still parser drafts, not human-reviewed gold labels.
- ASR-to-intent impact is not intent accuracy.
- The batch is still small and should not be treated as a final benchmark.
