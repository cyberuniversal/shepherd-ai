# MultiUAV Prompt, Runner, And Checkpoint Protocol

## Scope

This protocol implements the correctness-first infrastructure for CP-32,
CP-33, CP-34, and CP-39 without loading a model or running the unreviewed pilot.
The source-hashed contract artifact is
`datasets/multiuav_plat/runner_contract_audit_v1.json`.

## Prompt Contract

`src/shepherd_ai/multiuav_prompts.py` builds prompts only from:

- the validated AGENT-visible context;
- the frozen 11-endpoint action catalog; and
- the registered allowed observation endpoints.

It excludes proposed labels, reviewer fields, hidden references, official
plans, and privileged state. M1, M2, and M4 receive byte-equivalent first-call
messages and final-output schemas. M3 receives a distinct evidence-ledger
first call required by the registered stage-wise method.

Every prompt request records:

- prompt-contract version;
- method, call index, and call purpose;
- context SHA-256;
- complete messages and response contract; and
- request SHA-256.

## Method Calls

`src/shepherd_ai/multiuav_runner.py` accepts an injectable generation backend.
It does not depend on a specific provider or model library.

- M1: one final-output call, with no deterministic post-plan gate.
- M2: one final-output call, followed by deterministic grounding.
- M3: one evidence-ledger call, deterministic pre-plan checks, one mandatory
  final-output call, then deterministic grounding.
- M4: one candidate call, one learned-validator finalization call, then the
  common deterministic grounding gate.

M3 always makes its second call, including after ledger parse or provenance
failure. All raw generations, parse errors, intermediate ledgers, pre-plan
reports, and deterministic post-plan reports are retained. Backend exceptions
and invalid backend return types become explicit `BACKEND_ERROR` or
`BACKEND_PROTOCOL_ERROR` generation records, then flow into the final
`PARSE_ERROR` row instead of silently disappearing from the matrix.

The runner rejects `pending_human_review` before invoking a backend. Only
`approved_evaluation_case` and `synthetic_unit_fixture` statuses are runnable.
The latter is for unit tests and cannot be publication evidence.

The contract audit materializes all 150 unreviewed pilot cases and builds each
method's first prompt, for 600 prompt constructions total. It verifies exact
AGENT-context preservation and zero privileged or label-field leaks. This is a
prompt-isolation audit only; it does not invoke a model or approve any case.

## M3 Evidence Ledger

`src/shepherd_ai/multiuav_ledger_contract.py` strictly parses:

- visible evidence claims with AGENT-context source paths;
- missing operator facts;
- conflicts;
- a provisional decision; and
- a reason.

The deterministic pre-plan gate verifies source-path existence, rejects
privileged paths, and checks internal decision consistency. It does not prove
that a natural-language claim is semantically correct or that a missing fact
is truly unrecoverable.

## Checkpoint And Resume

`src/shepherd_ai/multiuav_checkpoints.py` binds a run to:

- immutable model ID and revision;
- dataset SHA-256;
- prompt version;
- exact methods;
- deterministic decoding settings;
- code commit; and
- run kind and ID.

The canonical run configuration produces a SHA-256 stored in the sidecar and
every JSONL result row. Each method-case result is appended, flushed, and
`fsync`-ed before the matrix advances. Resume rejects config drift, malformed
rows, duplicate result keys, model drift, and incomplete or unexpected
matrices.

`src/shepherd_ai/multiuav_experiment.py` skips already complete rows and makes
no backend call for them. It can write periodic deterministic ZIP checkpoints
every 250 newly appended rows by default, plus a final archive, containing:

- `run_config.json`;
- `results.jsonl`; and
- `manifest.json` with checksums and row count.

## Claim Limits

This infrastructure has only been exercised with scripted synthetic test
backends. No Qwen weights were cached, loaded, or invoked. No pilot row was
evaluated. The compact ZIP is not the final publication package, which must
also contain runtime metadata, summaries, figures, failure examples,
dependency versions, and code checksums.

## Reproduce

```powershell
python scripts/audit_multiuav_runner_contract.py `
  --output datasets/multiuav_plat/runner_contract_audit_v1.json

python -m unittest `
  tests.test_multiuav_prompts `
  tests.test_multiuav_ledger_contract `
  tests.test_multiuav_runner `
  tests.test_multiuav_checkpoints
```
