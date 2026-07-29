# MultiUAV Recursive Grounding Validator

## Scope

This protocol implements the deterministic post-plan portion of CP-34. It
validates parsed `EXECUTE` plans against only the AGENT-visible instruction and
context produced by `src/shepherd_ai/multiuav_context.py`. It never reads hidden
`related_apis`, `execution_check_apis`, official reference plans, targets,
obstacles, or `/check/*` results.

The implementation is
`src/shepherd_ai/multiuav_grounding_validator.py`. Its frozen machine-readable
contract is
`datasets/multiuav_plat/grounding_contract_audit_v1.json`.

## Containment Order

Validation stops at the first failing stage:

1. `post_plan_endpoint_schema`
2. `post_plan_identifier_grounding`
3. `post_plan_parameter_grounding`
4. `post_plan_safety_bounds`
5. `accepted`

Every issue includes a code, API-plan path, message, and rejected value.
Every successfully grounded parameter leaf includes its plan path, semantic
parameter class, value, visible source path, and grounding basis.

## Frozen Endpoint Catalog

The catalog contains the 11 benchmark command endpoints observed in the pinned
MultiUAV-Plat source:

- `take_off`
- `land`
- `move_to`
- `move_towards`
- `move_along_path`
- `change_altitude`
- `hover`
- `rotate`
- `return_home`
- `take_photo`
- `broadcast`

The validator enforces endpoint-specific required and optional parameters,
primitive types, and recursive waypoint shape. The audit artifact stores the
exact schemas.

## Visible Evidence Rules

- UAV identifiers must exactly match an AGENT-visible drone ID.
- Explicit instruction numbers may ground numeric parameters, except numbers
  used in `Drone N` or `UAV N` identity mentions.
- Coordinates may also match visible drone position or home-position
  coordinates of the same coordinate class.
- Altitude may also match visible position or home-position `z`.
- Heading may also match a visible drone heading or a registered compass
  direction in the instruction.
- Distance and duration require an explicit instruction number.
- Broadcast messages must be a normalized substring of the instruction.
- Waypoint coordinates are checked recursively and independently.

Canvas dimensions and maximum altitude are limits, not grounding evidence.
This prevents a model from inventing a value merely because the same number
appears in an unrelated visible field.

## Static Bounds

After grounding succeeds:

- `x` and `y` must remain inside the visible canvas;
- `z` and altitude must remain within the selected UAV's visible maximum;
- heading must be in `[0, 360)`; and
- distance and duration must be positive.

## Claim Limits

Passing this validator means only that a plan has an allowed static API shape,
visible-evidence provenance, and valid registered bounds. It does not establish
instruction fidelity, dynamic feasibility, collision avoidance, execution
success, or mission success. Equal visible numeric values can remain
semantically ambiguous within a compatible parameter class.

No model was loaded or invoked to create the contract audit. Method-runner
integration and revised-study evaluation remain unimplemented.

## Reproduce

```powershell
python scripts/audit_multiuav_grounding_contract.py `
  --output datasets/multiuav_plat/grounding_contract_audit_v1.json

python -m unittest tests.test_multiuav_grounding_validator
```
