# Command Datasets

This directory stores labeled natural-language command datasets for Week 2 intent extraction.

## Files

- `roadmap_examples.jsonl`: small roadmap-derived smoke examples.
- `intent_labeled_synthetic.jsonl`: synthetic, literature-guided command dataset for initial supervised intent extraction. It currently contains 26 records: 18 train, 4 validation, and 4 test.
- `human_written_commands_draft.jsonl`: raw manual collection file with deterministic draft labels.
- `human_written_commands_curated_v1.jsonl`: assistant-curated labels from the manual Week 2 command collection, split into 30 train, 10 validation, and 10 test records.

## Schema

Each JSONL record must include:

- `id`: stable unique identifier.
- `text`: command text or transcript.
- `split`: `train`, `validation`, or `test`.
- `source`: provenance string.
- `data_type`: for example `synthetic_command`, `human_written_command`, or `human_verified_transcript`.
- `expected_intent`: JSON object with `action`, `count`, `location`, `target`, and `constraints`.

Span-labeled command datasets use a separate schema documented in `docs/week2_span_annotation.md`. They include exact character spans for fields such as `target`, `location`, and `constraint`, and can be exported to BIO token labels with `scripts/validate_span_dataset.py`.

## Research Integrity

The current labeled dataset is synthetic and self-authored. It is useful for pipeline development, training-code tests, and baseline comparisons, but it is not evidence of real user performance or speech performance.

Do not mix synthetic, human-written, and ASR-derived examples without preserving `source`, `data_type`, and split metadata.

Do not duplicate command text across train, validation, and test splits.

Use `docs/week2_data_collection_protocol.md` before adding human-written commands, recorded-audio transcripts, or ASR-derived records.

Validate a command dataset before training or evaluation:

```powershell
python scripts/validate_command_dataset.py --dataset datasets/commands/intent_labeled_synthetic.jsonl --summary-output outputs/evaluations/intent_labeled_synthetic_summary.json --require-splits train,validation,test
```

Validate a span-labeled command dataset and export BIO token labels:

```powershell
python scripts/validate_span_dataset.py --dataset datasets/commands/human_verified_span_commands.jsonl --summary-output outputs/evaluations/human_verified_span_commands_summary.json --bio-output outputs/evaluations/human_verified_span_commands_bio.jsonl
```

To collect a typed transcript and optional WAV quickly:

```powershell
python scripts/collect_week2_sample.py --text "Send two drones north and inspect the crops." --wav "C:\path\to\your_recording.wav" --split train
```

This writes draft-labeled records to `datasets/commands/human_written_commands_draft.jsonl`. Review draft labels before using them as verified training or evaluation labels.
