# Week 2 Audio Split Policy

## Purpose

The Week 2 audio manifest now has explicit `train`, `validation`, and `test` labels so ASR results can be summarized by split instead of reporting only one pooled metric.

## Current Split

The current `datasets/sample_audio/manifest.jsonl` split is a deterministic 6/2/2 split over the 10 current `manual_week2_collection_v1` records:

- Train: `audio_001`, `audio_002`, `audio_004`, `audio_006`, `audio_008`, `audio_010`
- Validation: `audio_003`, `audio_005`
- Test: `audio_007`, `audio_009`

## Split Method

The split was produced by:

1. Sorting record IDs.
2. Shuffling with Python `random.Random(17)`.
3. Assigning the first 6 shuffled IDs to `train`, the next 2 to `validation`, and the final 2 to `test`.
4. Writing the split labels back into `datasets/sample_audio/manifest.jsonl` while leaving audio paths and transcripts unchanged.

The seed is `17` to match the other Week 2 training/evaluation scripts.

## Research Integrity Caveat

This is a retrospective split policy because an initial pooled Whisper ASR evaluation had already been recorded before the split was assigned. Treat the split-level metrics as a more informative breakdown of the existing sample, not as a clean final held-out benchmark.

A stronger ASR benchmark still requires newly collected audio records whose split is assigned before transcription/evaluation results are inspected.
