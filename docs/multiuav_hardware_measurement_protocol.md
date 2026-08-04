# MultiUAV Hardware Measurement Protocol

## Scope

Hardware measurement is separate from the deterministic accuracy run. The
accuracy matrix runs once per immutable checkpoint. Resource measurements use
30 stratified source-task clusters, all five variants, and three separately
hashed repetitions per model-method condition.

`datasets/multiuav_plat/resource_schedule_candidate_v1.json` now records a
deterministic candidate selection of two eligible held-out source tasks from
each of the 15 scenario/difficulty strata. It also records all 24 combinations
of two models, four methods, and three repetitions in a seeded order. This is a
source-task and condition-order manifest only. It is not final until every
selected source task has a complete approved five-case cluster and the final
dataset hash is bound into run configs. The config builder exists but refuses
any data status other than `approved_evaluation_data`. No study resource
measurement has run.

## Measurement Unit

The measured unit is one complete method-case. It includes all model calls and
the deterministic validation work for that method. Measuring individual calls
would undercount the two-call M3 and M4 configurations.

`run_kind="resource"` requires a resource-monitor factory. Accuracy and
synthetic-smoke configurations reject that factory. Each resource run binds:

- repetition index 1, 2, or 3;
- hardware-protocol artifact SHA-256; and
- model, dataset, prompt, decoding, and code revisions.

The expanded checkpoint contract is schema version 3. Resource configs bind
the repetition, condition order, resource-schedule hash, and hardware-protocol
hash. Config creation rejects candidate or otherwise unapproved data status.

## Recorded Metrics

- complete method-case wall-clock duration;
- input and output tokens from every model call;
- actual model-call count;
- process resident memory;
- NVIDIA board VRAM use;
- process GPU memory when NVML exposes it;
- GPU utilization and temperature diagnostics; and
- NVIDIA GPU-board energy.

Energy is not total workstation, simulator, network, or UAV energy.

## Energy Method

The primary source is `nvmlDeviceGetTotalEnergyConsumption`, reported by NVML
in millijoules. When that counter is unsupported, power is sampled at a target
20 Hz and integrated with the trapezoidal rule. Power integration is also
retained as a diagnostic when the counter exists, including its relative
difference from the counter.

NVML sampling uses the `nvidia-ml-py` bindings. Process resident memory uses
`psutil`. Raw samples remain in each resource report.

## Synthetic Probe

`datasets/multiuav_plat/hardware_measurement_contract_audit_v1.json` records a
synthetic timed-sleep probe on the GTX 1650 SUPER. It invoked no model and used
no study case. The probe confirmed that the NVML counter is available and raw
20 Hz-targeted telemetry is retained. Its energy value is infrastructure
evidence only and must not enter study tables, figures, or conclusions.

## Remaining Controls

Before a resource run, the following must still be frozen and tested:

- revalidation of the candidate subset against complete approved clusters;
- final dataset, code-commit, and hardware-artifact bindings for 24 run configs;
- warm-up procedure;
- idle and thermal-start conditions;
- treatment of background GPU workloads;
- fixed precision and checkpoint-specific offload configuration; and
- failed or invalid measurement-row handling in publication summaries.

These are implementation blockers, not reasons to use unreviewed cases.

## Reproduce The Probe

```powershell
python scripts/audit_multiuav_hardware_protocol.py `
  --output datasets/multiuav_plat/hardware_measurement_contract_audit_v1.json `
  --gpu-index 0
```

Rebuild the source-task and condition-order candidate with:

```powershell
python scripts/build_multiuav_resource_schedule.py `
  --output datasets/multiuav_plat/resource_schedule_candidate_v1.json
```
