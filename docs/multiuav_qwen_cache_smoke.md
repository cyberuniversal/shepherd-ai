# Qwen 2.5 Cache And Synthetic Load Smokes

## Scope

This record documents real-weight preflights for both Qwen checkpoints in the
active MultiUAV study. It does not use the unreviewed intervention pilot and is
not an accuracy, planning-quality, latency, or energy result.

## Cached Models

- Machine-local cache root:
  `D:\Users\momoa\shepherd-ai-runtime\hf-cache`

| Model | Immutable revision | Files | Bytes | Safetensors shards | Weight bytes |
|---|---|---:|---:|---:|---:|
| `Qwen/Qwen2.5-3B-Instruct` | `aa8e72537993ba99e69dfaafa59ed015b17504d1` | 12 | 6,183,464,935 | 2 | 6,171,926,992 |
| `Qwen/Qwen2.5-7B-Instruct` | `a09a35458c702b33eeacc393d103063234e8bc28` | 14 | 15,242,807,270 | 4 | 15,231,271,888 |

Every snapshot file has a SHA-256 record in the corresponding
`qwen25_3b_cache_audit_v1.json` or `qwen25_7b_cache_audit_v1.json` artifact.
Model files remain outside Git. Each cache artifact also binds the acquisition
and inventory source code. A checkout on another machine must acquire and
reverify its own cache.

## Runtime

- Python: 3.12.10
- PyTorch: 2.7.1+cu118
- Transformers: 4.57.6
- Accelerate: 1.14.0
- GPU: NVIDIA GeForce GTX 1650 SUPER, 4 GB
- Loading policy: float16 with `device_map=auto`
- Network policy: Python-process non-loopback socket guard plus Hugging Face
  and Transformers offline environment flags

Both checkpoints exceed available VRAM. Accelerate offloaded 3B parameters to
CPU memory and 7B parameters to CPU memory and an explicit external directory
on `D:`. Neither was a full-GPU run.

## Preserved Failed Attempt

The first load attempt passed the Hub model ID to Transformers with
`local_files_only=True`. Transformers 4.57.6 still attempted a metadata request
while patching tokenizer behavior. The socket guard blocked the request before
model loading, producing `NetworkIsolationError`. No model was invoked.

That negative result is preserved at
`datasets/multiuav_plat/qwen25_3b_load_smoke_attempt1_failed_v1.json`.
The backend was corrected to load directly from the checksum-verified immutable
snapshot directory, removing the remote-ID interpretation from the offline
path.

## Successful Smokes

Each current run:

- reverified all cached file hashes before loading;
- proved a non-loopback DNS request was blocked;
- loaded the pinned safetensors checkpoint from the local snapshot;
- invoked the model on one explicitly synthetic mission fixture;
- generated one token with greedy decoding from 769 input tokens; and
- retained the token-limited raw output without parsing or repair.

The current 3B run recorded 20.328 seconds generation latency and peak
allocated VRAM of 3,117,709,312 bytes. The 7B run recorded 128.104 seconds
generation latency and peak allocated VRAM of 3,795,313,664 bytes. The 7B run
used explicit disk offload and took 300.974 seconds from post-cache validation
through artifact completion.

The outputs reached their one-token limits and are truncated. They were not
parsed, repaired, scored, or interpreted as valid API plans. Complete raw
outputs and runtime metadata are stored in the corresponding
`qwen25_3b_load_smoke_v1.json` and `qwen25_7b_load_smoke_v1.json` artifacts with
claim status
`pinned_qwen_loaded_and_invoked_on_synthetic_fixture_not_study_evidence`.

The earlier successful 3B run generated 32 tokens and is preserved at
`qwen25_3b_load_smoke_pre_offload_option_v1.json`. It is historical
infrastructure evidence tied to the pre-offload-option source hash, not the
active smoke artifact.

## Reproduce

Use a Python 3.12 environment with the declared `multiuav-inference`
dependencies. Keep temporary files, package caches, and model files on a drive
with sufficient space.

```powershell
python scripts/cache_multiuav_qwen.py `
  --cache-dir D:\path\to\hf-cache `
  --output datasets/multiuav_plat/qwen25_3b_cache_audit_v1.json

python scripts/smoke_multiuav_qwen.py `
  --cache-audit datasets/multiuav_plat/qwen25_3b_cache_audit_v1.json `
  --output datasets/multiuav_plat/qwen25_3b_load_smoke_v1.json `
  --dtype float16 `
  --device-map auto `
  --max-new-tokens 1

python scripts/cache_multiuav_qwen.py `
  --model-id Qwen/Qwen2.5-7B-Instruct `
  --revision a09a35458c702b33eeacc393d103063234e8bc28 `
  --cache-dir D:\path\to\hf-cache `
  --output datasets/multiuav_plat/qwen25_7b_cache_audit_v1.json

python scripts/smoke_multiuav_qwen.py `
  --cache-audit datasets/multiuav_plat/qwen25_7b_cache_audit_v1.json `
  --output datasets/multiuav_plat/qwen25_7b_load_smoke_v1.json `
  --dtype float16 `
  --device-map auto `
  --offload-folder D:\path\to\offload\qwen25-7b `
  --max-new-tokens 1
```

## Remaining Boundaries

- No pilot, calibration, test, or other study case was evaluated.
- The Python socket guard is not an operating-system firewall.
- This smoke does not freeze the hardware measurement protocol.
- The truncated outputs are not evidence of model correctness or plan validity.
- The 7B smoke does not establish that full M1-M4 runs are practical on this
  4 GB GPU.
