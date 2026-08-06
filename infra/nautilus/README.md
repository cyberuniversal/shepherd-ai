# Nautilus MultiUAV Accuracy Execution

This directory defines the cluster path for the locked MultiUAV accuracy
experiment in namespace `aiea-interns`. It does not contain credentials.

The stages are deliberately separate:

1. `pvc.yaml` creates persistent storage for pinned weights, audits, raw rows,
   summaries, and checkpoints.
2. `cache-job.yaml` is the only networked model-acquisition stage. It downloads
   both immutable Qwen revisions over standard HTTP with Xet disabled and
   records every cached file checksum. An existing completed 3B audit is reused
   only after its immutable identity, research-integrity flags, file presence,
   and file sizes pass. The smoke stage still re-hashes every file before model
   loading. Automatic job retries are disabled so a failed attempt cannot
   silently duplicate work.
3. `smoke-job.yaml` requests one A100 and performs one synthetic, offline-guarded
   load/generation smoke for each cached checkpoint. It evaluates no study case.
4. `accuracy-3b-job.yaml` runs the locked 3B matrix at normal priority on a
   controlled GPU allowlist with at least 11 GiB, preferring an RTX 3090. It
   uses the cluster cache and smoke audits, writes one durable JSONL row per
   completed method-case, and creates periodic
   ZIP checkpoints. It never reads hidden scoring labels. Disruptions marked
   `DisruptionTarget` do not consume the bounded retry
   budget; replacement pods revalidate the cache and resume durable rows.
5. `accuracy-7b-job.yaml` runs the second locked matrix only after the 3B raw
   checkpoint is preserved. It uses the same score-blind runner and normal
   priority, but restricts scheduling to 24 GiB-or-larger GPUs because the
   registered 7B smoke reserved 15.43 GB before full-length generation.

Every job template contains `__SHEPHERD_GIT_COMMIT__`. Replace it with the exact
committed repository state that contains the final run configurations before
applying the job. Do not point a job at a moving branch.

The smoke and accuracy jobs operate with Hugging Face and Transformers offline
mode enabled. They may clone the pinned Shepherd-AI commit if its checkout is
not already on the PVC, but they cannot fetch or substitute model weights.

```powershell
kubectl apply -f infra/nautilus/pvc.yaml

$commit = git rev-parse HEAD
(Get-Content infra/nautilus/cache-job.yaml -Raw).Replace(
  '__SHEPHERD_GIT_COMMIT__', $commit
) | kubectl apply -f -

kubectl wait --for=condition=complete job/shepherd-ai-cache-models `
  -n aiea-interns --timeout=2h
```

Only submit the smoke job after the cache job completes, and only submit the
accuracy job after both smoke artifacts pass. Preserve failed jobs and their
logs before deleting or replacing any Kubernetes object.

The first local 3B feasibility attempt is retained separately under
`datasets/multiuav_plat/failed_attempts/`. It is excluded from the locked matrix
and must not be resumed or merged into cluster results.
