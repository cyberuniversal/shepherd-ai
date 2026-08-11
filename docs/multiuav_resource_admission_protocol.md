# MultiUAV Resource Admission Protocol

## Purpose

Resource admission is the score-blind boundary between preserved execution
artifacts and registered aggregate analysis. It determines whether the complete
resource campaign is structurally and procedurally eligible for analysis. It
does not calculate latency, energy, RAM, VRAM, or temperature statistics and it
does not inspect model outputs or hidden official labels.

## Frozen Inputs

The gate consumes these repository artifacts:

- `resource-v1-attempt3-complete.tar.gz` and its independent source manifest;
- the preservation manifest containing the outer archive and source-manifest
  hashes;
- `resource_run_configs_v1.json`;
- `resource_schedule_v1.json`;
- `resource_hardware_protocol_v1.json`;
- `accuracy_case_manifest_v1.json`; and
- `intervention_dataset_v1.json`.

The run registry, schedule, hardware protocol, approved manifest, and
intervention dataset are hashed again at admission. The gate accepts only the
registered 3 repetitions, 2 models, 4 methods, 24 conditions, 150 rows per
condition, and 3,600 total rows.

## Fail-Closed Checks

Admission rejects the campaign if any check fails:

1. The tar archive has an absolute path, parent traversal, duplicate member,
   link, device, extra file, missing file, or source-manifest hash/size drift.
2. The preservation manifest, archive, source manifest, schedule, protocol,
   approved data, or final run registry no longer agree.
3. A repetition/order condition is missing, duplicated, or bound to a different
   model, method, revision, commit, schedule, protocol, or approved manifest.
4. A checkpoint does not contain exactly `manifest.json`, `results.jsonl`, and
   `run_config.json`, or its internal hashes, row count, sidecar, raw JSONL
   source hash, or run summary differ.
5. A condition does not contain its exact 150 scheduled case-method rows in the
   frozen order, including valid result keys and nested identities.
6. Retained telemetry cannot independently reproduce its sample count, sample
   rate, duration bound, summaries, process inventory, energy counter or
   trapezoidal integration, GPU identity, or frozen protocol validation.
7. A referenced start-control report is absent or its self-hash, warm-up,
   baseline, idle/thermal recovery, process isolation, protocol hash, or
   attempt-wide node/GPU lock differs.
8. Campaign or condition summaries claim inspection, scoring, an incomplete
   matrix, an invalid condition, or a different preflight GPU.

These checks parse row metadata and telemetry only. The validator never reads
the model-behavior fields inside `result`, never loads official command labels,
and never derives study outcomes.

## Output And Next Gate

An accepted report has status
`complete_resource_campaign_admitted_for_analysis`, records every input and
validator hash, and explicitly records:

- `raw_model_outputs_inspected: false`;
- `hidden_labels_accessed: false`;
- `resource_scores_computed: false`; and
- `scored_rows: 0`.

Only that report authorizes the separately registered aggregate resource
analysis. Admission itself is not a resource result.

## Reproduce

```powershell
python scripts/admit_multiuav_resource_campaign.py
```

The default output is
`datasets/multiuav_plat/resource_campaign_admission_v1.json`.
