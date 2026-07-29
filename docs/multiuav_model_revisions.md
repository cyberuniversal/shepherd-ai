# MultiUAV Model Revision Lock

## Scope

CP-35 requires both registered Qwen checkpoints to resolve to immutable
40-character commits before model inference. The code-level registry is
`src/shepherd_ai/multiuav_model_revisions.py`.

The frozen revisions are:

| Role | Model | Immutable revision |
|---|---|---|
| Primary scale | `Qwen/Qwen2.5-3B-Instruct` | `aa8e72537993ba99e69dfaafa59ed015b17504d1` |
| Confirmation scale | `Qwen/Qwen2.5-7B-Instruct` | `a09a35458c702b33eeacc393d103063234e8bc28` |

On 2026-07-29, each Hugging Face immutable revision endpoint returned the exact
registered model ID and commit. The response subset, retrieval timestamp, and
source-code hashes are stored in
`datasets/multiuav_plat/model_revision_audit_v1.json`.

## Claim Limits

Revision resolution verifies model identity and immutability only. It does not
mean that weights were downloaded, cached, loaded, or invoked. It does not
establish package compatibility, offline isolation, deterministic decoding,
resource feasibility, or model quality.

The 3B repository reports the Qwen Research license through its model metadata;
the 7B repository reports Apache-2.0. License compliance and redistribution
requirements must be checked before packaging weights. Weights must not be
committed to Git.

## Reproduce

Remote metadata verification:

```powershell
python scripts/audit_multiuav_model_revisions.py `
  --output datasets/multiuav_plat/model_revision_audit_v1.json
```

Offline registry smoke test:

```powershell
python scripts/audit_multiuav_model_revisions.py `
  --skip-remote-verification `
  --output outputs/multiuav/model_revision_offline_smoke.json
```

Offline output must not be substituted for the stored remote-verification
artifact.
