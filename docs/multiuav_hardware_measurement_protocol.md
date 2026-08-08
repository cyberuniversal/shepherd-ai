# MultiUAV Hardware Measurement Protocol

## Scope

Hardware measurement is separate from the deterministic accuracy run. The
accuracy matrix runs once per immutable checkpoint. Resource measurements use
30 stratified source-task clusters, all five variants, and three separately
hashed repetitions per model-method condition.

`datasets/multiuav_plat/resource_schedule_v1.json` binds the deterministic
candidate selection to 30 complete, approved, held-out source-task clusters,
all 150 dependent variant cases, and all 24 combinations of two models, four
methods, and three repetitions. Each repetition has one frozen case order
shared by every model-method condition. The schedule is bound to the approved
manifest, intervention dataset, candidate schedule, and hardware protocol by
SHA-256. No study resource measurement has run.

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

## Frozen Execution Controls

`datasets/multiuav_plat/resource_hardware_protocol_v1.json` freezes one
NVIDIA GeForce RTX 3090, one physical node and GPU UUID for the full attempt,
float16 with `device_map=auto` and no offload, exact runtime package versions,
and complete method-case measurement. Model loading, warm-up, and idle waiting
are excluded from the measured unit.

Every condition process performs five idle baseline samples, one unretained
complete method-case warm-up, and then requires 15 consecutive one-second
samples at no more than 5% utilization and no more than 2 C above baseline or
60 C absolute. Baseline temperature may not exceed 60 C. NVML compute-process
enumeration must show exactly one GPU process both during the start control and
throughout every measured case. A node/GPU UUID lock prevents incompatible
resume.

Every row is durably appended. Any invalid row invalidates and preserves the
whole 150-row condition; a replacement must use a new attempt directory.
Publication summaries exclude invalid conditions. The campaign keeps raw
outputs unscored until the separate resource admission and analysis gate.

All 24 run configs are commit-bound. The remaining pre-measurement gate is a
no-inference RTX 3090 cluster preflight that independently verifies the 3B and
7B config, cache inventory, successful smoke audit, runtime, and GPU binding.
Final condition admission also resolves every row's start-control hash to its
untampered warm-up, thermal, and hardware-lock report.

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

Rebuild the final protocol and approved schedule without model invocation:

```powershell
python scripts/freeze_multiuav_resource_protocol.py
```
