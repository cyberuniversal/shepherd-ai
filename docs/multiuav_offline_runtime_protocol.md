# MultiUAV Local Qwen And Offline Runtime Protocol

## Scope

This protocol originally implemented the code-level portion of LP-48 without
downloading weights or running the unreviewed intervention pilot. Separate
artifacts now record real pinned 3B and 7B caches and synthetic
load/generation smokes.

The implementation is:

- `src/shepherd_ai/multiuav_qwen_backend.py`
- `src/shepherd_ai/multiuav_offline_runtime.py`
- `datasets/multiuav_plat/offline_runtime_contract_audit_v1.json`
- `datasets/multiuav_plat/qwen25_3b_cache_audit_v1.json`
- `datasets/multiuav_plat/qwen25_3b_load_smoke_v1.json`
- `datasets/multiuav_plat/qwen25_7b_cache_audit_v1.json`
- `datasets/multiuav_plat/qwen25_7b_load_smoke_v1.json`

## Model Loading

The backend accepts only the two model ID and immutable revision pairs frozen
in `src/shepherd_ai/multiuav_model_revisions.py`.

Both tokenizer and causal-language-model loading require:

- `revision` equal to the registered 40-character commit;
- `local_files_only=True`;
- `trust_remote_code=False`;
- safetensors model loading; and
- an optional explicit cache directory; and
- an optional recorded offload directory for checkpoints that exceed available
  GPU and CPU memory.

The real smokes supply the checksum-verified snapshot directories directly.
This prevents Transformers from treating the registered model ID as a remote
lookup target during offline loading. The snapshot directory basename must
equal the pinned revision and remain inside the registered cache root.

The 7B smoke also supplies an explicit external offload directory on `D:`.
Transformers and Accelerate may place parameters on GPU, CPU, or disk under
`device_map=auto`; that placement is infrastructure feasibility evidence, not
a frozen resource-measurement configuration.

Missing cached files are a preflight failure. The measured path must never
download a replacement or fall back to a mutable revision.

## Deterministic Generation Contract

Every call:

- applies the checkpoint's chat template with a generation prompt;
- uses `do_sample=False`;
- uses `num_beams=1`;
- uses a registered positive `max_new_tokens`;
- runs under PyTorch inference mode;
- returns only newly generated tokens to the method runner; and
- records model identity, revision, package versions, device, dtype, token
  counts, call latency, and the offline policy.

Greedy decoding is deterministic at the decoding-policy level. This is not a
claim of model correctness or bitwise equality across different hardware,
drivers, kernels, or package versions.

## Offline Isolation

During local model loading and generation, the process:

- sets `HF_HUB_OFFLINE=1`;
- sets `TRANSFORMERS_OFFLINE=1`;
- blocks non-loopback calls through `socket.socket.connect`;
- blocks non-loopback calls through `socket.socket.connect_ex`;
- blocks non-loopback `socket.create_connection`; and
- blocks non-loopback `socket.getaddrinfo`.

Loopback access remains available. The guard restores prior environment values
after use.

This is Python-process isolation, not an operating-system firewall, container
boundary, or proof that native extensions cannot open sockets. The final paper
must report that limitation. A measured run should add an external network
control when the execution environment permits it.

## Data Gate

`LocalQwenBackend` implements the provider interface consumed by the frozen
M1-M4 runner. The runner still rejects `pending_human_review` before backend
invocation. Only approved evaluation cases or explicit synthetic unit fixtures
are runnable.

No study case was evaluated while implementing this protocol.

## Dependencies

Install the optional inference dependencies only in the model environment:

```powershell
python -m pip install -e .[multiuav-inference]
```

Weights are setup artifacts and must not be committed. Both caches, complete
file checksums, runtime hardware metadata, the failed first 3B load, and all
successful synthetic smokes are documented in
`docs/multiuav_qwen_cache_smoke.md`.

## Reproduce

```powershell
python scripts/audit_multiuav_offline_runtime.py `
  --output datasets/multiuav_plat/offline_runtime_contract_audit_v1.json

python -m unittest `
  tests.test_multiuav_offline_runtime `
  tests.test_multiuav_qwen_backend `
  tests.test_audit_multiuav_offline_runtime_cli
```

## Claim Limits

The current evidence establishes a tested backend, process-level isolation,
and real 3B and 7B synthetic load/generation smokes. It does not establish
that:

- the 3B checkpoint fits fully in 4 GB VRAM;
- the 7B checkpoint is practical for full experiments on this machine;
- any intervention label is approved;
- any M1-M4 method is accurate;
- resource measurement is implemented; or
- LP-48 is complete end to end.
