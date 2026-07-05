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
- Post-hoc `deterministic_v2` intent impact: `outputs/evaluations/whisper_base_audio_generalization_intent_impact_v2_local_gtx1650.json`
- Human-reviewed audio intent labels: `datasets/commands/audio_generalization_human_verified_intents.jsonl`
- Human-reviewed intent-label summary: `outputs/evaluations/audio_generalization_human_verified_intents_summary.json`
- Initial human-reviewed intent accuracy: `outputs/evaluations/whisper_base_audio_generalization_intent_accuracy_human_verified_local_gtx1650.json`
- Post-hoc `deterministic_v2` human-reviewed intent accuracy: `outputs/evaluations/whisper_base_audio_generalization_intent_accuracy_human_verified_v2_local_gtx1650.json`

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

This compares parser/model outputs on human transcripts versus Whisper transcripts. It is useful for isolating ASR-induced changes, but the gold-label accuracy section below is the stronger intent-extraction evaluation for this batch.

For both historical `deterministic_v1` and `trained_nb_human_curated_v2`:

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

## Human-Reviewed Intent Accuracy

The audio generalization batch now has 30 human-reviewed audio intent labels:

- Label file: `datasets/commands/audio_generalization_human_verified_intents.jsonl`
- Label source: `human_reviewed_v1`
- Data type: `human_verified_audio_intent_command`
- Split: 10 validation, 20 test
- Readiness check: passed, with 0 draft records and 0 unreviewed records

The reviewed labels were normalized to the current Week 2 single-action schema. Review notes mark schema-gap commands such as mapping, monitoring, allocation-like division, and compound send-then-return instructions.

Gold intent accuracy using the existing local-GPU Whisper predictions:

| System | Transcript | Exact Record Accuracy | Field Accuracy | Main Field Errors |
| --- | --- | ---: | ---: | --- |
| `deterministic_v1` | human transcript | 7 / 30 = 0.2333 | 0.6667 | target 18, location 16, constraints 9, action 7 |
| `deterministic_v1` | Whisper transcript | 4 / 30 = 0.1333 | 0.6133 | target 20, location 16, action 10, constraints 9, count 3 |
| `trained_nb_human_curated_v2` | human transcript | 7 / 30 = 0.2333 | 0.6667 | target 18, location 16, constraints 9, action 7 |
| `trained_nb_human_curated_v2` | Whisper transcript | 4 / 30 = 0.1333 | 0.6133 | target 20, location 16, action 10, constraints 9, count 3 |

This result is much lower than the earlier audio-linked metric because the earlier metric reused overlapping typed-command labels. The reviewed non-overlapping audio labels are a stricter test and show that Week 2 intent extraction still needs substantial improvement.

After reviewing those errors, the deterministic baseline was revised to `deterministic_v2`. This is a post-hoc iteration, not a clean final benchmark on the same data. It adds rule coverage for location-target separation in `X for Y` commands, map/monitor/photograph normalization, open-vocabulary location phrases, compound-command constraints, and a few observed ASR confusions.

Post-hoc `deterministic_v2` result:

| System | Transcript | Exact Record Accuracy | Field Accuracy | Main Field Errors |
| --- | --- | ---: | ---: | --- |
| `deterministic_v2` | human transcript | 27 / 30 = 0.9000 | 0.9600 | location 3, target 1, constraints 1, action 1 |
| `deterministic_v2` | Whisper transcript | 19 / 30 = 0.6333 | 0.8933 | target 6, location 5, constraints 2, count 2, action 1 |
| `trained_nb_human_curated_v2` with v2 rule overrides | human transcript | 27 / 30 = 0.9000 | 0.9600 | location 3, target 1, constraints 1, action 1 |
| `trained_nb_human_curated_v2` with v2 rule overrides | Whisper transcript | 19 / 30 = 0.6333 | 0.8933 | target 6, location 5, constraints 2, count 2, action 1 |

## Interpretation

This batch shows that the earlier 10-record result was too optimistic for broader claims. Whisper still performs reasonably, but the non-overlapping batch introduces real recognition errors on mission-critical words such as actions, drone counts, and targets.

The canonical constraint normalizer handled number-format changes in the historical run, so altitude-like numeric substitutions did not become canonical constraint changes. Under `deterministic_v2`, one canonical constraint change remains in the ASR-impact analysis because `stay below sixty meters` becomes `stay below 60 meters` and the current normalizer does not yet canonicalize `stay below ...` phrasing. Action/target/count errors remain important because they can change the downstream mission representation.

## Current Limitations

- This is a local GTX run, not a Colab/T4 run.
- The reviewed labels use the current single-action Week 2 schema, so compound commands and monitoring/allocation-like requests are lossy.
- `deterministic_v2` was developed after inspecting this reviewed batch, so its same-batch score is post-hoc and needs a fresh held-out audio batch.
- ASR-to-intent impact is a consistency analysis; the gold intent accuracy result is reported separately above.
- The audio files remain untracked; only the manifest and outputs are documented.
