# Week 2 Post-Development Benchmark Protocol

Purpose: create the clean benchmark that the current Week 2 work is missing.

## Why This Exists

The existing Week 2 artifacts include real training and evaluation work, but the current primary handoff is still provisional. `deterministic_v3` was developed after inspecting earlier holdout errors, and the trained transformer span path is not reliable enough for final intent JSON on the 30-record audio transcript benchmark.

This protocol creates a fresh benchmark after that development history.

## Required Workflow

1. Create a blank fresh audio collection packet.
2. Record new WAV files.
3. Write human-verified transcripts.
4. Audit the manifest for overlap against all prior command, span, and audio transcript text.
5. Run Whisper ASR on the fresh manifest.
6. Create an audio-intent review packet.
7. Human-review the intent labels.
8. Validate that the reviewed intent labels are ready for gold evaluation.
9. Evaluate the deterministic parser, trained text baseline, transformer span assembly, and hybrid span parser on the same frozen benchmark.
10. Run `scripts/audit_week2_completion.py`.

## Commands

Create a blank post-development packet:

```powershell
python scripts/create_week2_audio_generalization_packet.py `
  --commands datasets/commands/human_written_commands_curated_v1.jsonl `
  --spans datasets/commands/human_verified_span_commands.jsonl `
  --existing-audio-manifest datasets/sample_audio/manifest.jsonl `
  --existing-audio-manifest datasets/sample_audio/audio_generalization_manifest.jsonl `
  --existing-audio-manifest datasets/sample_audio/audio_v2_holdout_manifest.jsonl `
  --dataset-root . `
  --jsonl-output reports/week2_post_development_audio_packet.jsonl `
  --markdown-output reports/week2_post_development_audio_packet.md `
  --record-prefix audio_postdev `
  --source manual_week2_post_development_audio_v1 `
  --validation-count 10 `
  --test-count 20
```

After filling the new manifest and adding WAV files, audit it:

Build the manifest from the filled packet:

```powershell
python scripts/build_audio_manifest_from_packet.py `
  --packet reports/week2_post_development_audio_packet.jsonl `
  --dataset-root . `
  --manifest-output datasets/sample_audio/audio_post_development_manifest.jsonl `
  --summary-output outputs/evaluations/audio_post_development_manifest_summary.json
```

```powershell
python scripts/audit_week2_audio_generalization_manifest.py `
  --candidate-manifest datasets/sample_audio/audio_post_development_manifest.jsonl `
  --commands datasets/commands/human_written_commands_curated_v1.jsonl `
  --spans datasets/commands/human_verified_span_commands.jsonl `
  --existing-audio-manifest datasets/sample_audio/manifest.jsonl `
  --existing-audio-manifest datasets/sample_audio/audio_generalization_manifest.jsonl `
  --existing-audio-manifest datasets/sample_audio/audio_v2_holdout_manifest.jsonl `
  --dataset-root . `
  --output outputs/evaluations/week2_post_development_manifest_audit.json `
  --fail-on-overlap
```

Validate the Week 2 gate:

```powershell
python scripts/audit_week2_completion.py
```

## Research Rules

- Do not run ASR before the fresh split and human transcript are recorded.
- Do not reuse command text from old datasets.
- Set each collected packet row to `"collection_status": "human_transcript_verified"` only after listening to the WAV and checking the transcript.
- Do not mark labels as human-reviewed until a human checks them.
- Preserve failed ASR and weak transformer results.
- Keep ASR evaluation separate from intent evaluation.
