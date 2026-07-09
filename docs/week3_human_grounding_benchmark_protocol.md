# Week 3 Human Grounding Benchmark Protocol

## Purpose

This protocol describes how to resolve the remaining Week 3 blocker: `human_collected_grounding_benchmark_exists`.

The current repository contains synthetic grounding datasets. They are useful for regression testing, but they are not human-collected grounding evidence.

## Collection Packet

Generate the blank packet with:

```powershell
python scripts/create_week3_human_grounding_packet.py --map datasets/maps/shepherd_test_map_v1.csv --jsonl-output reports/week3_human_grounding_packet.jsonl --markdown-output reports/week3_human_grounding_packet.md
```

The generated packet contains:

- one blank command slot for each of the 20 main synthetic map records,
- one ambiguous `road` command slot,
- one unresolved-object command slot.

## Human Collection Rules

For each slot:

- a human must write one natural command in the `text` field,
- the command should follow the slot instruction,
- the expected grounding label should remain unchanged unless the command no longer matches the slot,
- blank slots must not be copied into `datasets/maps/` as benchmark data,
- model-generated text must not be labeled as human-written data.

## Completion Conditions

The human benchmark exists only after:

- the completed JSONL is saved under `datasets/maps/`,
- every record has non-empty human-written `text`,
- `label_status` is no longer `needs_human_written_command`,
- `data_type` identifies the records as human-collected or human-written grounding benchmark records,
- `scripts/validate_grounding_dataset.py` passes against the completed dataset,
- `scripts/evaluate_grounding.py` runs on the completed dataset,
- `scripts/audit_week3_completion.py` is regenerated with the completed human benchmark evidence.

Expected command sequence after the packet is filled:

```powershell
python scripts/finalize_week3_human_grounding_packet.py --packet reports/week3_human_grounding_packet.jsonl --output datasets/maps/human_grounding_benchmark_v1.jsonl
python scripts/validate_grounding_dataset.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/human_grounding_benchmark_v1.jsonl --summary-output outputs/evaluations/human_grounding_benchmark_v1_validation.json
python scripts/evaluate_grounding.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/human_grounding_benchmark_v1.jsonl --output outputs/evaluations/human_grounding_benchmark_v1.json
python scripts/audit_week3_completion.py --map-validation outputs/evaluations/map_validation_shepherd_test_map_v1.json --region-map-validation outputs/evaluations/map_validation_shepherd_test_map_regions_v1.json --grounding-evaluation outputs/evaluations/grounding_examples_v1.json --grounding-evaluation outputs/evaluations/grounding_diagnostics_v1.json --grounding-evaluation outputs/evaluations/grounding_holdout_synthetic_v1.json --grounding-dataset-validation outputs/evaluations/grounding_examples_v1_validation.json --grounding-dataset-validation outputs/evaluations/grounding_diagnostics_v1_validation.json --grounding-dataset-validation outputs/evaluations/grounding_holdout_synthetic_v1_validation.json --coverage-report outputs/evaluations/grounding_map_coverage_v1.json --week3-status outputs/evaluations/week3_grounding_status.json --acceptance-criteria docs/week3_acceptance_criteria.json --research-deferrals docs/week3_research_deferrals.json --human-grounding-dataset-validation outputs/evaluations/human_grounding_benchmark_v1_validation.json --human-grounding-evaluation outputs/evaluations/human_grounding_benchmark_v1.json --json-output outputs/evaluations/week3_completion_gate_audit.json --markdown-output reports/week3_completion_gate_audit.md
```

## Current Status

Implemented for the current Week 3 synthetic-map scope. The repository contains:

- `reports/week3_human_grounding_packet.jsonl`
- `reports/week3_human_grounding_packet.md`
- `datasets/maps/human_grounding_benchmark_v1.jsonl`
- `outputs/evaluations/human_grounding_benchmark_v1_validation.json`
- `outputs/evaluations/human_grounding_benchmark_v1.json`

Current result: 22 / 22 exact records and 22 / 22 reference matches.

This is human-written command evidence over the custom synthetic Week 3 map. It is not real-world map grounding evidence.
