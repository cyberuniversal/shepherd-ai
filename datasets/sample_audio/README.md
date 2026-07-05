# Sample Audio Dataset

This directory stores roadmap Week 2 WAV command recordings and transcript manifests.

Current contents:

- 10 WAV command recordings.
- `manifest.jsonl` with human-provided transcripts.
- Source: `manual_week2_collection_v1`.
- Data type: `human_recorded_audio`.
- Current split: all 10 records are `train`.

Do not add private recordings, large audio files, or generated model outputs without documenting source, consent/licensing status, transcript provenance, split, and preprocessing.

Use a JSONL manifest with the schema documented in `docs/milestone_2_speech_input.md`.

Validate a manifest before using it:

```powershell
python scripts/validate_audio_manifest.py --manifest datasets/sample_audio/manifest.jsonl --dataset-root . --summary-output outputs/evaluations/audio_manifest_summary.json
```

Fast collection path:

```powershell
python scripts/collect_week2_sample.py --text "Send two drones north and inspect the crops." --wav "C:\path\to\your_recording.wav" --split train
```

WAV files copied here are ignored by Git by default.

Run Whisper ASR in Colab/T4 after installing `openai-whisper`:

```powershell
python scripts/transcribe_audio_whisper.py --manifest datasets/sample_audio/manifest.jsonl --dataset-root . --predictions-output outputs/evaluations/whisper_base_audio_predictions.jsonl --evaluation-output outputs/evaluations/whisper_base_audio_evaluation.json --model base --device cuda --language en --required-device-substring T4
```

Current recorded ASR artifact set is from a local `NVIDIA GeForce GTX 1650 SUPER` GPU run, not Colab/T4:

- `outputs/evaluations/whisper_base_audio_predictions_local_gtx1650.jsonl`
- `outputs/evaluations/whisper_base_audio_evaluation_local_gtx1650.json`
- `outputs/evaluations/whisper_base_audio_error_analysis_local_gtx1650.json`
