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

Resource runs use checkpoint schema version 3. Their config hashes additionally
bind repetition 1-3, condition order, the resource-schedule artifact, and the
hardware-protocol artifact. The run-config builder refuses any dataset status
other than `approved_evaluation_data`. A resource monitor wraps the complete
method-case and its report is retained in the same durable row. Accuracy runs
reject resource monitors so hardware repetitions remain separate from the
locked deterministic accuracy matrix.

`src/shepherd_ai/multiuav_publication.py` provides a separate fail-closed
accuracy admission gate. It accepts only complete matrices from `accuracy`
runs whose rows are all `approved_evaluation_case`, rejects any resource
measurement or synthetic fixture, and retains parse-error rows for scoring.
It has synthetic unit coverage but has not admitted or scored study data.

`src/shepherd_ai/multiuav_scoring.py` is the downstream, label-separated scorer.
It re-parses retained raw outputs, verifies stored deterministic reports, derives
post-gate system disposition, applies the external grounding validator to M1-M4,
and records official-command fidelity from hidden upstream labels. Its frozen
audit read no study checkpoint row.

## Claim Limits

The provider-independent runner has only been exercised with scripted
synthetic test backends. A local Qwen implementation now exists under
`docs/multiuav_offline_runtime_protocol.md`. The pinned 3B and 7B checkpoints
were cached, checksummed, loaded, and invoked directly for synthetic backend
smokes, but neither has been exercised through the full M1-M4 experiment
runner. No pilot row was evaluated. The compact ZIP is not the final publication
package, which must also contain runtime metadata, summaries, figures, failure
examples, dependency versions, and code checksums.

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
