# Milestone 2: Speech-To-Text Input Scaffold

## Why This Comes Next

The roadmap places speech recognition and intent extraction in Week 2. Typed-command intent extraction is already implemented as the first baseline, so the next roadmap-aligned step is the speech input side of the same week.

The repository now has a small self-recorded WAV manifest and transcript set. The reproducibility scaffold remains explicit: audio manifest validation, transcript evaluation utilities, and a GPU-oriented Whisper transcription script.

## System Requirement Supported

This milestone supports the roadmap requirement to accept uploaded audio, convert speech to text using Whisper, and maintain corresponding transcripts for examples such as:

- `audio_001.wav` -> "Send two drones north and inspect the crops."
- `audio_002.wav` -> "Scan the western field."
- `audio_003.wav` -> "Return drone three."

## Baseline

Current baseline: cached or manually provided transcript text evaluated against expected transcript text.

Implemented and initially evaluated: `scripts/transcribe_audio_whisper.py`, which runs Whisper inference when Whisper is installed and writes raw predictions plus transcript metrics.

This baseline is intentionally narrow. It evaluates speech-to-text only; intent/span extraction evaluation remains separate.

## Required Data

Each audio command should be recorded as a WAV file and listed in a JSONL manifest with one record per line:

```json
{
  "id": "audio_001",
  "audio_path": "datasets/sample_audio/audio_001.wav",
  "transcript": "Send two drones north and inspect the crops.",
  "source": "self_recorded",
  "data_type": "human_recorded_audio",
  "split": "example"
}
```

Required fields:

- `id`: stable record identifier.
- `audio_path`: path to a WAV file under the dataset root.
- `transcript`: expected transcript.
- `source`: data source or collection method.
- `data_type`: label such as `human_recorded_audio`, `synthetic_audio`, or `cached_transcript`.
- `split`: example, train, validation, or test.

Current audio data:

- 10 WAV recordings under `datasets/sample_audio/`.
- Manifest: `datasets/sample_audio/manifest.jsonl`.
- Source: `manual_week2_collection_v1`.
- Data type: `human_recorded_audio`.
- Current split after the retrospective seed-17 policy: 6 `train`, 2 `validation`, and 2 `test` records. See `docs/week2_audio_split_policy.md`.

## Evaluation

The scaffold provides:

- Exact transcript match after normalization.
- Word error rate using word-level edit distance.
- Metadata fields for model name, model version, parameters, and generation time.
- Raw Whisper prediction JSONL output when `scripts/transcribe_audio_whisper.py` is run.

Raw evaluation output should remain under `outputs/evaluations/`.

Recorded local-GPU ASR run, July 4, 2026:

- Environment: local Windows GPU run, not Google Colab.
- Device: `NVIDIA GeForce GTX 1650 SUPER`.
- Model: Whisper `base`.
- Command flags: `--device cuda`, `--language en`, `--required-device-substring GTX`, `--no-fp16`.
- Reason for local run: the WAV files are intentionally not tracked by Git, so the Colab clone cannot access them without uploading private audio or committing recordings to the public repository.
- Raw predictions: `outputs/evaluations/whisper_base_audio_predictions_local_gtx1650.jsonl`.
- Evaluation: `outputs/evaluations/whisper_base_audio_evaluation_local_gtx1650.json`.
- Error analysis: `outputs/evaluations/whisper_base_audio_error_analysis_local_gtx1650.json`.
- Split summary: `outputs/evaluations/whisper_base_audio_split_summary_local_gtx1650.json`.
- Intent impact analysis: `outputs/evaluations/whisper_base_intent_impact_local_gtx1650.json`.
- Intent accuracy analysis with matched command labels: `outputs/evaluations/whisper_base_intent_accuracy_local_gtx1650.json`.
- Span impact analysis with matched human-verified span labels: `outputs/evaluations/whisper_base_span_impact_local_gtx1650.json`.
- Pooled result on the 10-record sample: exact-match accuracy `0.9`, mean word error rate `0.01`.
- Observed normalized word substitution: `fifty -> 50`.
- Retrospective split-level result: train WER `0.0167`, validation WER `0.0`, test WER `0.0`.
- ASR-to-intent impact result: the normalized `fifty -> 50` substitution changes the raw extracted `constraints` string for one train record, but not the normalized semantic intent comparison or canonical altitude-constraint comparison. This is an impact/consistency result, not intent accuracy or safety validation.
- Audio-linked intent accuracy result: the 10 human transcripts match existing curated command labels. Human transcripts score exact-record accuracy `1.0`; Whisper transcripts score `0.9` due to the raw `fifty` versus `50` constraint string.
- ASR-to-span impact result: the 10 human transcripts match existing human-verified span labels. The local `span_nb_v1` baseline scores human-transcript span entity F1 `0.7324` on those matched records. Whisper changes one raw predicted `constraint` entity for `audio_006` because `fifty` becomes `50`, but the number-normalized semantic span comparison is unchanged. This is not ASR span accuracy because no human gold spans exist for the Whisper transcript text.

This is a real Whisper ASR evaluation on the current recorded WAVs, but it is not a Colab/T4 result and not a final held-out speech benchmark.

Recorded non-overlapping audio generalization run, July 5, 2026:

- Environment: local Windows GPU run, not Google Colab.
- Device: `NVIDIA GeForce GTX 1650 SUPER`.
- Model: Whisper `base`.
- Manifest: `datasets/sample_audio/audio_generalization_manifest.jsonl`.
- Report: `reports/week2_audio_generalization_asr_report.md`.
- Split: 10 validation and 20 test records.
- Non-overlap audit: 0 overlaps with existing command, span, or audio transcript text.
- Overall exact-match accuracy: `0.60`.
- Overall mean word error rate: `0.0716`.
- Validation exact-match accuracy: `0.70`; test exact-match accuracy: `0.55`.
- ASR-to-intent impact: 8 of 30 records changed raw intent outputs, and 7 of 30 changed semantic intent outputs after normalization.
- Human-reviewed audio-intent labels were later applied in `datasets/commands/audio_generalization_human_verified_intents.jsonl`.
- Initial `deterministic_v1` reviewed intent accuracy: 7 of 30 exact matches on human transcripts and 4 of 30 exact matches on Whisper transcripts.
- Post-hoc `deterministic_v2` reviewed intent accuracy: 27 of 30 exact matches on human transcripts and 19 of 30 exact matches on Whisper transcripts.
- The `deterministic_v2` result is not a clean final benchmark because the parser was revised after inspecting this reviewed batch.

Next pre-registered audio holdout:

- Blank packet: `reports/week2_audio_v2_holdout_packet.md` and `reports/week2_audio_v2_holdout_packet.jsonl`.
- Slots: 10 validation and 20 test records.
- Source for future records: `manual_week2_audio_v2_holdout_v1`.
- Overlap blocklist: existing curated commands, human-verified spans, `datasets/sample_audio/manifest.jsonl`, and `datasets/sample_audio/audio_generalization_manifest.jsonl`.
- Purpose: test whether `deterministic_v2` generalizes beyond the batch that motivated it.

Recorded v2 holdout ASR run, July 5, 2026:

- Manifest: `datasets/sample_audio/audio_v2_holdout_manifest.jsonl`.
- Report: `reports/week2_audio_v2_holdout_asr_report.md`.
- Environment: local Windows GPU run, not Google Colab.
- Device: `NVIDIA GeForce GTX 1650 SUPER`.
- Model: Whisper `base`.
- Split: 10 validation and 20 test records.
- Non-overlap audit: 0 overlaps with existing command, span, or audio transcript text.
- Overall exact-match accuracy: `0.7333`.
- Overall mean word error rate: `0.0485`.
- Validation exact-match accuracy: `0.6000`; test exact-match accuracy: `0.8000`.
- ASR-to-intent impact with `deterministic_v2`: 5 of 30 records changed semantic intent outputs.
- Draft intent review packet: `reports/week2_audio_v2_holdout_intent_review_packet.jsonl`.
- Gold intent accuracy: not evaluated yet because the v2 holdout intent labels are still drafts.

Run Whisper in Colab/T4:

```powershell
python scripts/transcribe_audio_whisper.py `
  --manifest datasets/sample_audio/manifest.jsonl `
  --dataset-root . `
  --predictions-output outputs/evaluations/whisper_base_audio_predictions.jsonl `
  --evaluation-output outputs/evaluations/whisper_base_audio_evaluation.json `
  --model base `
  --device cuda `
  --language en `
  --required-device-substring T4
```

## Successful Completion

This scaffold is complete when:

- Audio manifest records are validated before use.
- Paths cannot escape the dataset root.
- Transcript comparisons produce per-record and summary metrics.
- Tests pass.

The full speech-to-text milestone is not complete until the project defines a real audio split policy and, if Colab remains required, a private-audio upload workflow that does not publish WAV recordings to GitHub.

## Known Uncertainties

- Colab/T4 ASR is still not recorded because the WAV files are intentionally untracked and unavailable to a clean Colab clone.
- Whisper model size is currently planned as `base` for the first reproducible pass.
- Audio recording conditions are not stated.
- Language/accent/noise coverage is not stated.
- The current train/validation/test audio split is retrospective and therefore not a clean final held-out benchmark.
- Acceptance threshold for speech accuracy is not stated.
