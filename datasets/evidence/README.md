# Evidence-Decision Data

This directory stores labels and controlled cases for the Week 9
evidence-aware paper experiment.

## Current Files

- `week9_conflict_cases_v1.jsonl` contains four explicitly synthetic
  conflicting-reference controls.
- `week9_monolithic_diagnostic_gold_v1.jsonl` contains gold decisions for the
  reused 38-case diagnostic packet. It must never be loaded by the model
  inference runner.

The corresponding label-free model inputs are generated under
`outputs/evaluations/`.

## Fresh Human Benchmark Status

A fresh human-authored final-test benchmark is **not collected**. Do not call
the diagnostic gold file a fresh held-out result.

The implemented collection workflow uses separate files for frozen evidence
contexts, author labels, blinded reviewer labels, disagreement adjudication,
and the final benchmark. See
`docs/human_evidence_benchmark_protocol.md` for exact schemas and commands.

Each final adjudicated record contains:

```json
{
  "id": "evidence_human_001",
  "text": "human-authored command",
  "decision_stage": "grounding_sufficiency",
  "context_id": "heldout_context_001",
  "context_sha256": "hash of the exact frozen context",
  "expected_decision": "proceed",
  "label_rationale": "why the registered context supports this decision",
  "split": "final_test",
  "source": "manual_week9_evidence_collection_v1",
  "data_type": "human_written_evidence_decision",
  "author_id": "participant_001",
  "reviewer_id": "reviewer_001",
  "label_status": "adjudicated"
}
```

`author_id` and `reviewer_id` are pseudonymous identifiers and must differ.
Model-generated commands must retain a synthetic/model-generated data type and
cannot be inserted into this human benchmark.

Validate a completed candidate against existing command data:

```powershell
python scripts/validate_human_evidence_benchmark.py `
  --dataset datasets/evidence/human_evidence_benchmark_v1.jsonl `
  --contexts datasets/evidence/human_evidence_contexts_v1.jsonl `
  --comparison datasets/maps/human_grounding_benchmark_v1.jsonl `
  --comparison datasets/maps/grounding_holdout_synthetic_v1.jsonl `
  --comparison datasets/safety/week7_safety_cases_v1.jsonl `
  --summary-output outputs/evaluations/human_evidence_benchmark_v1_validation.json `
  --require-balanced
```

This validator checks schema, class balance, duplicate text, cross-dataset
overlap, adjudication status, author/reviewer separation, and exact frozen
context hashes. It cannot prove semantic label correctness or replace ethics
and participant-consent review.
