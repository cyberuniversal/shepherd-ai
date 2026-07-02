# Sample Audio Dataset

This directory is reserved for roadmap Week 2 WAV command recordings and transcript manifests.

No audio files are currently included. Do not add private recordings, large audio files, or generated model outputs without documenting source, consent/licensing status, transcript provenance, split, and preprocessing.

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
