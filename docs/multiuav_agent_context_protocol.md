# MultiUAV Agent-Visible Context Protocol

## Purpose

This protocol freezes the pre-planning evidence projection used to construct
the revised study's model inputs. It reproduces the pinned upstream AGENT role
conservatively and prevents hidden benchmark answers from entering prompts.

## Visible Before Planning

The projection contains only:

- the case instruction;
- a non-semantic task identifier;
- session ID, task type, canvas dimensions, distance mode, and status;
- the AGENT-visible drone list and operational drone fields;
- the current environment and weather fields; and
- an explicit list of allowed AGENT observation endpoints.

The projection deliberately omits source task names and descriptions because
they may restore information removed by a controlled intervention.

## Not Pre-Exposed

The projection recursively excludes:

- official aliases other than the selected case instruction;
- `related_apis`, `commands`, and `execution_check_apis`;
- `is_done` and `is_passed`;
- session history and statistics; and
- global target and obstacle records.

MultiUAV-Plat allows AGENT-role access to local target and obstacle observations
through drone-nearby endpoints. These are runtime evidence, not initial prompt
evidence. A method may request them only through the common allowed observation
contract.

## Audit

`scripts/audit_multiuav_agent_context.py` projects all 1,500 canonical source
tasks from the pinned archive. For every task it also mutates every privileged
source field and verifies that the projected context remains byte-equivalent
after canonical JSON serialization.

The committed summary is
`datasets/multiuav_plat/agent_context_audit_v1.json`. It contains counts,
source binding, and the role contract, not model prompts or benchmark answers.

## Claim Limits

This gate establishes prompt-field isolation only. It does not establish that
an intervention is valid, that missing information is unrecoverable, that a
resource conflict is real, or that any method plans or executes correctly.
