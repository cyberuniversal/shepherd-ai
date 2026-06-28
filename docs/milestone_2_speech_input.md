# Milestone 2: Speech-To-Text Input Scaffold

## Why This Comes Next

The roadmap places speech recognition and intent extraction in Week 2. Typed-command intent extraction is already implemented as the first baseline, so the next roadmap-aligned step is the speech input side of the same week.

The repository still has no WAV files, transcript dataset, Whisper package/version configuration, or train/test/evaluation split. Because of that, this milestone begins with the reproducibility scaffold that must exist before running Whisper: an audio manifest schema and transcript evaluation utilities.

## System Requirement Supported

This milestone supports the roadmap requirement to accept uploaded audio, convert speech to text using Whisper, and maintain corresponding transcripts for examples such as:

- `audio_001.wav` -> "Send two drones north and inspect the crops."
- `audio_002.wav` -> "Scan the western field."
- `audio_003.wav` -> "Return drone three."

## Baseline

Current baseline: cached or manually provided transcript text evaluated against expected transcript text.

Not implemented yet: Whisper inference.

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

No audio data is currently present in the repository.

## Evaluation

The scaffold provides:

- Exact transcript match after normalization.
- Word error rate using word-level edit distance.
- Metadata fields for model name, model version, parameters, and generation time.

Raw evaluation output should remain under `outputs/evaluations/`.

## Successful Completion

This scaffold is complete when:

- Audio manifest records are validated before use.
- Paths cannot escape the dataset root.
- Transcript comparisons produce per-record and summary metrics.
- Tests pass.

The full speech-to-text milestone is not complete until real WAV files, transcripts, Whisper dependency choices, model configuration, and transcript evaluation results exist.

## Known Uncertainties

- Exact Whisper package and version are not stated.
- Whisper model size is not stated.
- Audio recording conditions are not stated.
- Language/accent/noise coverage is not stated.
- Train/validation/test split policy is not stated.
- Acceptance threshold for speech accuracy is not stated.
