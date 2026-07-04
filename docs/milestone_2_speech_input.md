# Milestone 2: Speech-To-Text Input Scaffold

## Why This Comes Next

The roadmap places speech recognition and intent extraction in Week 2. Typed-command intent extraction is already implemented as the first baseline, so the next roadmap-aligned step is the speech input side of the same week.

The repository now has a small self-recorded WAV manifest and transcript set. Because Whisper ASR results have not yet been recorded, this milestone keeps the reproducibility scaffold explicit: audio manifest validation, transcript evaluation utilities, and a Colab/GPU-oriented Whisper transcription script.

## System Requirement Supported

This milestone supports the roadmap requirement to accept uploaded audio, convert speech to text using Whisper, and maintain corresponding transcripts for examples such as:

- `audio_001.wav` -> "Send two drones north and inspect the crops."
- `audio_002.wav` -> "Scan the western field."
- `audio_003.wav` -> "Return drone three."

## Baseline

Current baseline: cached or manually provided transcript text evaluated against expected transcript text.

Implemented but not yet evaluated: `scripts/transcribe_audio_whisper.py`, which runs Whisper inference when Whisper is installed and writes raw predictions plus transcript metrics.

This baseline is intentionally narrow. It lets the project validate dataset records and transcript metrics before introducing a speech model.

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
- Current split: all 10 records are `train`, so this is not yet a final ASR benchmark split.

## Evaluation

The scaffold provides:

- Exact transcript match after normalization.
- Word error rate using word-level edit distance.
- Metadata fields for model name, model version, parameters, and generation time.
- Raw Whisper prediction JSONL output when `scripts/transcribe_audio_whisper.py` is run.

Raw evaluation output should remain under `outputs/evaluations/`.

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

The full speech-to-text milestone is not complete until Whisper dependency/version metadata, model configuration, raw predicted transcripts, and transcript evaluation results are committed.

## Known Uncertainties

- Exact Whisper package and version will be recorded after the first ASR run.
- Whisper model size is currently planned as `base` for the first reproducible pass.
- Audio recording conditions are not stated.
- Language/accent/noise coverage is not stated.
- Train/validation/test split policy for audio is not finalized; the current 10 recordings are all marked `train`.
- Acceptance threshold for speech accuracy is not stated.
