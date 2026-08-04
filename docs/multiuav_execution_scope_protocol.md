# MultiUAV Static Execution Scope

## Decision

The primary study evaluates static plan fidelity. It does not submit plans to
the official MultiUAV-Plat server and does not execute missions in a live
simulator.

This follows the locked code plan: planning validity is static API, parameter,
and official-command fidelity unless plans are actually submitted to and
checked by the official server.

## Primary Metrics

- JSON and schema validity;
- endpoint validity;
- parameter grounding; and
- official-command fidelity during label-separated scoring.

These metrics may be described as static plan fidelity. They must not be
described as live mission success, simulator mission success, or physical-UAV
mission success.

The official reference plan and hidden validators remain unavailable to the
model. They may only be used later by label-separated scoring code.

## Upgrade Rule

Any future execution claim requires a new frozen scope version, actual plan
submission to the official server, retained server checks, and separate
execution results. Static results cannot be retroactively relabelled.

## Evidence

```powershell
python scripts/audit_multiuav_execution_scope.py `
  --output datasets/multiuav_plat/execution_scope_audit_v1.json
```

The stored audit invokes neither a model nor the official server.
