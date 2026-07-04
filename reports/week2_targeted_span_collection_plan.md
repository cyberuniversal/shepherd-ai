# Week 2 Targeted Span Collection Plan

This report is derived from the reviewed Colab/T4 transformer error analysis. It does not contain generated command text or new gold labels.

## Roadmap Anchor

- Week: Week 2
- Deliverables: speech-to-text pipeline, intent parser, example command dataset.
- Fields: action, count, location, target, constraint

## Current Reviewed Transformer Result

- Records: 10
- Entity F1: 0.6047
- Entity precision: 0.5652
- Entity recall: 0.6500
- Token accuracy: 0.7281

## Split Policy

- Put targeted follow-up records in train or validation only.
- Do not use targeted records derived from held-out test errors as an unbiased test result.
- Create a fresh test set later if these targeted categories become part of model selection.

## Field Priorities

### target

- Priority: high
- False negatives: 4
- False positives: 7
- Current span count: 42
- Heuristic requested new records: 11
- Collection guidance:
  - Collect commands where the target follows scan/inspect/search/capture wording.
  - Include object targets and inspection targets that appear near filler words such as for, of, and to.

### constraint

- Priority: high
- False negatives: 2
- False positives: 8
- Current span count: 10
- Heuristic requested new records: 10
- Collection guidance:
  - Collect commands with explicit restrictions, sequencing, or safety conditions.
  - Label only the full constraint phrase, not surrounding filler unless it is part of the condition.

### count

- Priority: high
- False negatives: 2
- False positives: 4
- Current span count: 36
- Heuristic requested new records: 6
- Collection guidance:
  - Collect commands with numeric counts, written counts, all-drones wording, and drone identifiers.
  - Keep count spans separate from target or drone-name spans.

### action

- Priority: medium
- False negatives: 4
- False positives: 1
- Current span count: 55
- Heuristic requested new records: 5
- Collection guidance:
  - Collect commands with more than one mission verb.
  - Include dispatch/send/return wording when it changes the action boundary.
  - Verify every action span manually instead of copying parser output.

### location

- Priority: medium
- False negatives: 2
- False positives: 0
- Current span count: 25
- Heuristic requested new records: 3
- Collection guidance:
  - Collect commands where area names can be confused with target names.
  - Include directional terms and named regions, then label only the phrase that grounds the mission location.

## Next Batch

- Minimum human-written span records: 35
- Record text policy: human_written_or_label_as_synthetic
- Label policy: human_verified_exact_character_spans

## Completion Criteria

- New records validate with scripts/validate_span_dataset.py.
- No normalized command text is duplicated across train, validation, and test splits.
- Hugging Face export is regenerated from the updated span dataset.
- Transformer retrain is run in Google Colab with a T4 runtime.
- Raw metrics, predictions, and error analysis are copied back before interpreting results.
