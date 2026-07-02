# Week 2 Span Annotation

## Purpose

The current field-level command datasets label whole intent fields such as `target: crops` or `location: north`. That is useful for early classification, but it is not enough for a stronger slot extractor. A trainable span or token model needs exact text spans showing where each field appears in the command.

This document defines the span-labeled dataset format for Week 2. It supports later spaCy or Hugging Face token-classification work without adding those dependencies yet.

## Why This Comes Next

The literature review supports bounded structured outputs and deterministic validation, but not a hand-written parser as the whole language-understanding system. Span labels let Shepherd-AI move from dictionary/parser coverage toward supervised extraction of mission fields from natural language.

This does not replace deterministic validators. It prepares a trainable semantic layer whose output can still be checked before grounding, planning, scheduling, or safety modules consume it.

## JSONL Schema

Each record is one command:

```json
{
  "id": "span_cmd_001",
  "text": "Capture images of the red pickup truck.",
  "split": "train",
  "source": "manual_week2_span_annotation_v1",
  "data_type": "human_verified_span_command",
  "spans": [
    {
      "field": "target",
      "start": 22,
      "end": 38,
      "text": "red pickup truck"
    }
  ]
}
```

Required fields:

- `id`: stable unique identifier.
- `text`: exact command text or verified transcript.
- `split`: `train`, `validation`, or `test`.
- `source`: provenance string.
- `data_type`: data type such as `human_verified_span_command`.
- `spans`: list of exact character spans.

Allowed span fields:

- `action`
- `count`
- `location`
- `target`
- `constraint`

Span rules:

- `text[start:end]` must exactly equal the span's `text`.
- Spans must not overlap.
- Spans must preserve the original command text, including capitalization and spacing.
- Parser-generated spans are drafts only unless reviewed by a human.

## Validation And BIO Export

Create one span-labeled command without manually counting character offsets:

```powershell
python scripts/create_span_record.py `
  --output datasets/commands/human_verified_span_commands.jsonl `
  --id span_cmd_001 `
  --text "Send the nearest drone to inspect the livestock pen without crossing the road." `
  --split train `
  --target-span "livestock pen" `
  --constraint-span "without crossing the road" `
  --action-span "inspect"
```

The `--*-span` values should be exact phrases copied from the command text. Matching is case-insensitive for convenience, and the saved span preserves the original text casing. If a phrase appears more than once, the script rejects it instead of guessing.

For compound commands such as `Send two drones north and inspect the crops.`, label the mission action that matches `expected_intent.action`. In this example, use `--action-span "inspect"`. Do not also label `Send` as an action unless the command's expected action is actually `send`.

To label a command that already exists in a command dataset, use its existing `id` and do not retype the command text:

```powershell
python scripts/create_span_record_from_command.py `
  --input datasets/commands/human_written_commands_curated_v1.jsonl `
  --id human_cmd_001 `
  --output datasets/commands/human_verified_span_commands.jsonl `
  --count-span "two drones" `
  --location-span "north" `
  --action-span "inspect" `
  --target-span "crops"
```

This copies the original `text`, `split`, and `expected_intent` from the source command record and adds traceability fields such as `base_command_id`.

## Rebuild From A Saved Command List

If you keep all span-label commands in a Notepad file, save it as something like:

```text
span_label_commands.txt
```

Then rebuild the whole span dataset from scratch:

```powershell
python scripts/rebuild_span_dataset_from_commands.py `
  --commands-file span_label_commands.txt `
  --output datasets/commands/human_verified_span_commands.jsonl `
  --summary-output outputs/evaluations/human_verified_span_commands_summary.json `
  --bio-output outputs/evaluations/human_verified_span_commands_bio.jsonl
```

The rebuild script only accepts lines that invoke `scripts/create_span_record_from_command.py`. It backs up the existing output file, writes a clean replacement, and validates/exports BIO labels. Use this when you want to replace old labels after editing the command list.

Validate a span dataset:

```powershell
python scripts/validate_span_dataset.py `
  --dataset datasets/commands/human_verified_span_commands.jsonl `
  --summary-output outputs/evaluations/human_verified_span_commands_summary.json
```

Export BIO token labels for later token-classification training:

```powershell
python scripts/validate_span_dataset.py `
  --dataset datasets/commands/human_verified_span_commands.jsonl `
  --summary-output outputs/evaluations/human_verified_span_commands_summary.json `
  --bio-output outputs/evaluations/human_verified_span_commands_bio.jsonl
```

The BIO export records tokens, character offsets, and labels such as `B-target`, `I-target`, and `O`.

## Review Queue From Model Errors

After a held-out token-classifier evaluation exists, build a review queue instead of editing the dataset from model predictions directly:

```powershell
python scripts/build_span_review_queue.py `
  --evaluation outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_predictions.json `
  --output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_queue.jsonl `
  --summary-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_summary.json `
  --focus-field target `
  --focus-field constraint
```

Each queue record keeps the original command, current gold tags, model-predicted tags, entity disagreements, and token errors. The queue is for human inspection only; it does not relabel the dataset.

Export the queued records into a Notepad-friendly command file:

```powershell
python scripts/export_span_review_commands.py `
  --span-dataset datasets/commands/human_verified_span_commands.jsonl `
  --review-queue outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_queue.jsonl `
  --commands-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_commands.txt `
  --report-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_report.md `
  --source-command-dataset datasets/commands/human_written_commands_curated_v1.jsonl
```

The command file starts from the current gold spans, not the model predictions. Use the Markdown report as context while editing. After human review, apply the reviewed subset back into the full span dataset:

```powershell
python scripts/apply_span_review_commands.py `
  --base-dataset datasets/commands/human_verified_span_commands.jsonl `
  --commands-file outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_commands.txt `
  --output datasets/commands/human_verified_span_commands.jsonl `
  --summary-output outputs/evaluations/human_verified_span_commands_summary.json `
  --bio-output outputs/evaluations/human_verified_span_commands_bio.jsonl
```

Use `apply_span_review_commands.py` for review subsets because it replaces only matching record IDs and preserves the rest of the dataset. Use `rebuild_span_dataset_from_commands.py` only when the command file is intended to recreate the entire span dataset.

## Research Integrity

Do not call a span dataset human-verified unless a human checked every span.

Do not train on validation or test records.

Do not report slot-extraction accuracy until a held-out span-labeled split exists.

Do not mix human-written commands, transcripts, ASR outputs, synthetic examples, and parser drafts without preserving `source`, `data_type`, and split metadata.
