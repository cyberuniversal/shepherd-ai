# Command Datasets

This directory stores labeled natural-language command datasets for Week 2 intent extraction.

## Files

- `roadmap_examples.jsonl`: small roadmap-derived smoke examples.
- `intent_labeled_synthetic.jsonl`: synthetic, literature-guided command dataset for initial supervised intent extraction.

## Schema

Each JSONL record must include:

- `id`: stable unique identifier.
- `text`: command text or transcript.
- `split`: `train`, `validation`, or `test`.
- `source`: provenance string.
- `data_type`: for example `synthetic_command`, `human_written_command`, or `human_verified_transcript`.
- `expected_intent`: JSON object with `action`, `count`, `location`, `target`, and `constraints`.

## Research Integrity

The current labeled dataset is synthetic and self-authored. It is useful for pipeline development, training-code tests, and baseline comparisons, but it is not evidence of real user performance or speech performance.

Do not mix synthetic, human-written, and ASR-derived examples without preserving `source`, `data_type`, and split metadata.

Do not duplicate command text across train, validation, and test splits.
