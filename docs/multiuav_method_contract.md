# MultiUAV Method And Output Contract

## Scope

This document freezes the model-call semantics and strict structural output
contract required by paragraphs 31 and 32 of
`docs/source_material/code_plan_2026-07-25.docx`. Prompt construction, runner
integration, and recursive grounding were implemented afterward under
`docs/multiuav_runner_checkpoint_protocol.md`. Learned-model inference,
execution, and evaluation remain absent.

## Model-Call Budget

Every method-case evaluation uses the following exact number of model calls:

| Method | Calls | Purpose |
|---|---:|---|
| `M1_monolithic` | 1 | Produce the decision and API plan together. |
| `M2_post_plan_deterministic` | 1 | Produce the M1-shaped output, then apply a non-model deterministic gate. |
| `M3_stage_wise` | 2 | First produce an evidence ledger and provisional decision; then produce the API plan or finalize a non-execution decision. Deterministic checks run before and after the second call. |
| `M4_post_plan_compute_matched` | 2 | First produce a decision and API plan; then use a separate learned post-plan validation call, followed by the common deterministic structural and grounding checks. |

M3 always makes its second call, including `CLARIFY` and `BLOCK` cases. The
second call finalizes the non-execution response without producing a plan.
Skipping it would break the registered per-case call-count match with M4.

The term `compute_matched` is limited to model-call count. It does not mean
equal tokens, latency, memory, or energy. Those quantities must be measured and
reported separately.

## Strict Model Output

Each final method output is exactly one JSON object with these fields:

```json
{
  "decision": "EXECUTE",
  "reason": "Non-empty explanation",
  "clarification_question": null,
  "api_plan": [
    {
      "endpoint": "/drones/{id}/command/take_off",
      "parameters": {
        "id": "registered-drone-id",
        "altitude": 20
      }
    }
  ]
}
```

The API-call representation follows the pinned MultiUAV-Plat
`related_apis` structure: an endpoint path and parameter object.

Decision invariants:

- `EXECUTE` requires a non-empty plan and a null clarification question.
- `CLARIFY` requires a non-empty question and an empty plan.
- `BLOCK` requires a null question and an empty plan.
- Every decision requires a non-empty reason.

The parser rejects additional or missing fields, code fences, commentary,
duplicate JSON keys, non-finite numbers, lowercase or invented decisions,
invalid endpoint paths, null or blank parameter values, and non-object
parameters.

Malformed output is preserved as `PARSE_ERROR` with its raw text and error
code. It is never repaired, discarded, or converted into a valid decision.

## Boundary With Grounding

The strict parser validates syntax and structural invariants only. By itself,
it does not establish endpoint, identifier, or value grounding. The separate
deterministic grounding validator now checks:

- an endpoint exists in the allowed AGENT API catalog;
- an identifier is present in visible context;
- coordinates, headings, distances, and messages are visibly grounded; and
- registered static bounds.

Neither component proves that the complete plan matches the operator's intent
or that the mission would succeed in the official server.

Grounding behavior and limitations are frozen in
`docs/multiuav_grounding_validator_protocol.md`.

## Frozen Artifact

Run:

```powershell
python scripts/audit_multiuav_method_contract.py `
  --output datasets/multiuav_plat/method_contract_audit_v1.json
```

The artifact records the method registry, call counts, strict field sets,
source-code hashes, and the parser's claim boundary.
