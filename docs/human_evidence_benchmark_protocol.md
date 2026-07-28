# Fresh Human Evidence Benchmark Protocol

> **Historical protocol:** This workflow belongs to the superseded Week 9
> evidence-aware paper direction. Preserve it for traceability, but do not use
> it as the primary dataset protocol for the active MultiUAV-Plat
> validation-placement study. See
> `docs/multiuav_validation_study_protocol.md`.

## Purpose

This protocol creates the fresh, adjudicated final-test evidence-decision
benchmark required by `docs/week9_monolithic_baseline_protocol.md`. It tests
whether a system selects `proceed`, `clarify`, or `block` from a human-written
command and a frozen simulation-evidence context.

The workflow does not generate human commands, assign human identities, or
invent labels. Those actions require real participants. A completed dataset is
not a Shepherd-AI result until both systems are run and their raw outputs are
stored.

## Experimental Scope

- Commands are human written.
- Evidence contexts may describe the software simulation; they are not claims
  about physical drones or real-world conditions.
- Sampling is class-balanced by construction, so the benchmark does not
  estimate operational class prevalence.
- Contexts, labels, and splits are frozen before model inference.
- The command author and independent reviewer use different pseudonymous IDs.
- A third person adjudicates disagreements and must differ from both.
- Existing development commands are excluded by normalized-text comparison.
- Model-generated commands cannot use the
  `human_written_evidence_decision` data type.

The final sample size and participant/ethics procedure are not stated by the
roadmap or literature-review documents. Register those decisions before
collection rather than adding them after observing results.

## Files

Use these names for the first collection:

```text
datasets/evidence/human_evidence_contexts_v1.jsonl
datasets/evidence/human_evidence_author_v1.jsonl
datasets/evidence/human_evidence_review_v1.jsonl
datasets/evidence/human_evidence_adjudications_v1.jsonl
datasets/evidence/human_evidence_benchmark_v1.jsonl
outputs/evaluations/human_evidence_blinded_review_v1.jsonl
outputs/evaluations/human_evidence_blinded_review_manifest_v1.json
outputs/evaluations/human_evidence_disagreements_v1.jsonl
outputs/evaluations/human_evidence_adjudication_summary_v1.json
outputs/evaluations/human_evidence_benchmark_v1_validation.json
outputs/evaluations/human_evidence_monolithic_inputs_v1.jsonl
datasets/evidence/human_evidence_monolithic_gold_v1.jsonl
outputs/evaluations/human_evidence_monolithic_manifest_v1.json
```

Do not create the final benchmark by editing model predictions.

## Record Contracts

One frozen context record:

```json
{
  "context_id": "heldout_context_001",
  "decision_stage": "grounding_sufficiency",
  "stage_definition": "criterion shown to the systems",
  "evidence": {"map_records": []},
  "source": "manual_week9_context_collection_v1",
  "data_type": "registered_simulation_evidence_context"
}
```

One author record:

```json
{
  "id": "evidence_human_001",
  "text": "human-written command",
  "decision_stage": "grounding_sufficiency",
  "context_id": "heldout_context_001",
  "author_decision": "proceed",
  "author_rationale": "reason based only on the frozen context",
  "split": "final_test",
  "source": "manual_week9_evidence_collection_v1",
  "data_type": "human_written_evidence_decision",
  "author_id": "participant_001"
}
```

One independent review record:

```json
{
  "id": "evidence_human_001",
  "reviewer_id": "reviewer_001",
  "reviewer_decision": "proceed",
  "reviewer_rationale": "independent reason based on the blinded packet"
}
```

For a disagreement only, one adjudication record:

```json
{
  "id": "evidence_human_001",
  "adjudicator_id": "adjudicator_001",
  "final_decision": "clarify",
  "adjudication_rationale": "why this label follows from the frozen evidence"
}
```

Allowed stages are `grounding_sufficiency`, `preflight`, and
`compound_grounding_and_preflight`. Allowed decisions are `proceed`,
`clarify`, and `block`.

## Procedure

1. Register the collection target, class allocation, context sources, and
   participant procedure before writing commands.
2. Create and freeze the context JSONL.
3. Have the author write commands and initial labels in the author JSONL.
4. Generate a label-blinded packet:

```powershell
python scripts/prepare_human_evidence_review.py `
  --author-dataset datasets/evidence/human_evidence_author_v1.jsonl `
  --contexts datasets/evidence/human_evidence_contexts_v1.jsonl `
  --output outputs/evaluations/human_evidence_blinded_review_v1.jsonl `
  --manifest-output outputs/evaluations/human_evidence_blinded_review_manifest_v1.json
```

5. Give only the blinded packet to the independent reviewer. Store their
   decisions in the review JSONL.
6. Merge agreements and identify disagreements:

```powershell
python scripts/adjudicate_human_evidence_benchmark.py `
  --author-dataset datasets/evidence/human_evidence_author_v1.jsonl `
  --review-dataset datasets/evidence/human_evidence_review_v1.jsonl `
  --contexts datasets/evidence/human_evidence_contexts_v1.jsonl `
  --output datasets/evidence/human_evidence_benchmark_v1.jsonl `
  --disagreements-output outputs/evaluations/human_evidence_disagreements_v1.jsonl `
  --summary-output outputs/evaluations/human_evidence_adjudication_summary_v1.json
```

The command exits unsuccessfully while disagreements remain unresolved. Add
`--adjudications datasets/evidence/human_evidence_adjudications_v1.jsonl` only
after the third party records decisions, then rerun it.

7. Validate balance, overlap, identities, and frozen context hashes:

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

8. Freeze label-separated model inputs:

```powershell
python scripts/build_human_evidence_model_packet.py `
  --benchmark datasets/evidence/human_evidence_benchmark_v1.jsonl `
  --contexts datasets/evidence/human_evidence_contexts_v1.jsonl `
  --inputs-output outputs/evaluations/human_evidence_monolithic_inputs_v1.jsonl `
  --gold-output datasets/evidence/human_evidence_monolithic_gold_v1.jsonl `
  --manifest-output outputs/evaluations/human_evidence_monolithic_manifest_v1.json
```

The model runner receives only the input JSONL. The evaluator receives raw
predictions and the separate gold JSONL after inference.

## Completion Gate

Collection is ready for inference only when:

- every planned case has a distinct human-written command;
- every context hash resolves and the context stage matches the case stage;
- every case has an independent review;
- every disagreement has third-party adjudication;
- all three decision classes are balanced;
- no command overlaps a registered development comparison dataset;
- the validation summary reports `valid: true`; and
- the model-packet manifest and all source hashes are stored.

Semantic label correctness still depends on human review. File validation
cannot replace participant consent, ethics review, or an evaluation protocol.
