# Week 2 Audio Generalization ASR Report

This report summarizes the first non-overlapping Week 2 audio generalization batch. It is a stronger test than the earlier 10-record audio sample because the transcripts do not normalize-match existing command, span, or audio transcript text.

## Batch

- Manifest: `datasets/sample_audio/audio_generalization_manifest.jsonl`
- Records: 30
- Split: 10 validation, 20 test
- Source: `manual_week2_audio_generalization_v1`
- Data type: `human_recorded_audio`
- Non-overlap audit: `outputs/evaluations/week2_audio_generalization_manifest_audit.json`
- Audit result: 0 overlap records, 0 duplicate candidate transcripts

## ASR Run

- Model: Whisper `base`
- Runtime: local Windows GPU run, not Colab/T4
- Device: `NVIDIA GeForce GTX 1650 SUPER`
- Python: 3.12.10
- Torch: 2.12.1+cu126
- openai-whisper: 20250625
- Flags: `--device cuda --language en --required-device-substring GTX --no-fp16`

Artifacts:

- Raw predictions: `outputs/evaluations/whisper_base_audio_generalization_predictions_local_gtx1650.jsonl`
- Transcript evaluation: `outputs/evaluations/whisper_base_audio_generalization_evaluation_local_gtx1650.json`
- Error analysis: `outputs/evaluations/whisper_base_audio_generalization_error_analysis_local_gtx1650.json`
- Split summary: `outputs/evaluations/whisper_base_audio_generalization_split_summary_local_gtx1650.json`
- Intent impact: `outputs/evaluations/whisper_base_audio_generalization_intent_impact_local_gtx1650.json`

## ASR Metrics

- Overall exact transcript accuracy: 18 / 30 = 0.60
- Overall mean word error rate: 0.0716
- Validation exact transcript accuracy: 7 / 10 = 0.70
- Validation mean word error rate: 0.0947
- Test exact transcript accuracy: 11 / 20 = 0.55
- Test mean word error rate: 0.0600

Word-level error analysis:

- Error records: 12
- Substitutions: 16
- Insertions: 3
- Deletions: 1

Examples of substantive substitutions include:

- `inspect -> expect`
- `survey -> server`
- `drones -> jones`
- `drone -> drawn`
- `service -> entrance`
- `cart -> card`
- `two -> to`

Number normalizations also occurred:

- `five -> 5`
- `six -> 6`
- `sixty -> 60`

## Downstream Intent Impact

This is not intent accuracy because the new audio batch does not yet have separate human-verified intent labels. It compares parser/model outputs on human transcripts versus Whisper transcripts.

For both `deterministic_v1` and `trained_nb_human_curated_v2`:

- Raw transcript changed records: 15 / 30
- Normalized word changed records: 12 / 30
- Raw intent changed records: 8 / 30
- Semantic intent changed records: 7 / 30
- Canonical constraint changed records: 0 / 30

Changed fields before semantic normalization:

- `action`: 3
- `constraints`: 1
- `count`: 3
- `target`: 3

Changed fields after semantic normalization:

- `action`: 3
- `count`: 3
- `target`: 3

## Interpretation

This batch shows that the earlier 10-record result was too optimistic for broader claims. Whisper still performs reasonably, but the non-overlapping batch introduces real recognition errors on mission-critical words such as actions, drone counts, and targets.

The canonical constraint normalizer handled number-format changes, so altitude-like numeric substitutions did not become canonical constraint changes. However, action/target/count errors remain important because they can change the downstream mission representation.

## Current Limitations

- This is a local GTX run, not a Colab/T4 run.
- The batch has human transcripts and audio, but not separate human-verified intent labels.
- ASR-to-intent impact is a consistency analysis, not gold intent accuracy.
- The audio files remain untracked; only the manifest and outputs are documented.
