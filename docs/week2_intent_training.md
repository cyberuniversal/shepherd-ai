# Week 2 Intent Training

## Scope

This document covers the first literature-driven Week 2 training pass: supervised text-command intent extraction.

The roadmap identifies Week 2 as speech recognition and intent extraction. The literature review indicates that a hand-written parser is only a baseline. A serious implementation needs labeled data, held-out evaluation, structured outputs, and comparison against baselines.

## Implemented

- Synthetic labeled command dataset: `datasets/commands/intent_labeled_synthetic.jsonl`.
- Split-aware dataset loader and validator.
- Trainable field-level multinomial Naive Bayes model for `action`, `location`, and `target`.
- Rule-based count and constraint extraction reused from the deterministic parser.
- Held-out test evaluation.
- Comparison against deterministic parser `deterministic_v0`.
- Raw metrics under `outputs/evaluations/`.
- Lightweight JSON model artifact under `outputs/model_artifacts/`.

## Command

```powershell
python scripts/train_intent_model.py `
  --dataset datasets/commands/intent_labeled_synthetic.jsonl `
  --model-output outputs/model_artifacts/intent_nb_v0.json `
  --metrics-output outputs/evaluations/intent_nb_v0_metrics.json `
  --comparison-output outputs/evaluations/intent_nb_v0_vs_deterministic.json `
  --seed 17
```

## Initial Result

Dataset: `intent_labeled_synthetic.jsonl`

Split:

- Train: 18 records
- Validation: 4 records
- Test: 4 records

Held-out synthetic test result for `trained_nb_v0`:

- Field accuracy: 0.85
- Exact-record accuracy: 0.25

Comparison on the same synthetic test records:

- `deterministic_v0`: field accuracy 1.0, exact-record accuracy 1.0
- `trained_nb_v0`: field accuracy 0.85, exact-record accuracy 0.25

Interpretation: the trained baseline is currently weaker than the deterministic parser on this tiny synthetic test set. This is a negative/early result and should be preserved. It is not evidence that the final trained approach is ineffective; it shows that the current dataset and model are too small and simple.

## Not Implemented

- No real human-written command collection.
- No real WAV dataset.
- No Whisper ASR evaluation.
- No transformer or spaCy fine-tuning yet.
- No grounding, planning, scheduling, vision, safety validation, or end-to-end mission evaluation.

## Next Training Work

- Expand labeled commands with more paraphrases and edge cases.
- Add human-written typed commands if available.
- Evaluate deterministic parser and trained model by data type.
- Add a stronger spaCy or Hugging Face baseline once dataset size justifies it.
- Evaluate intent extraction separately on gold transcripts and ASR transcripts when audio exists.
