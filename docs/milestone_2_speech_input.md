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
- Current split: all 10 records are `train`, so this is not yet a final ASR benchmark split.

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
- Result on the 10-record train-marked sample: exact-match accuracy `0.9`, mean word error rate `0.01`.

This is a real Whisper ASR evaluation on the current recorded WAVs, but it is not a Colab/T4 result and not a final held-out speech benchmark.

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
- Train/validation/test split policy for audio is not finalized; the current 10 recordings are all marked `train`.
- Acceptance threshold for speech accuracy is not stated.
