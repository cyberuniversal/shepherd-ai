# Week 7 Mission Supervision Evaluation

This is a synthetic event-driven lifecycle evaluation, not physical-flight safety evidence.

## Summary

- Cases: `8`
- Expected final-status matches: `8`
- Expected event-sequence matches: `8`
- Expected intervention matches: `8`

## Cases

| Case | Expected | Actual | Events match | Interventions |
| --- | --- | --- | --- | --- |
| week7_supervision_complete_001 | completed | completed | True | none |
| week7_supervision_battery_001 | intervention_required | intervention_required | True | return_to_launch_requested |
| week7_supervision_availability_001 | paused | paused | True | hold_and_replan_requested |
| week7_supervision_pause_resume_001 | completed | completed | True | none |
| week7_supervision_cancel_001 | cancelled | cancelled | True | none |
| week7_supervision_restricted_001 | blocked | blocked | True | none |
| week7_supervision_separation_001 | paused | paused | True | hold_and_replan_requested |
| week7_supervision_multistep_separation_001 | paused | paused | True | hold_and_replan_requested |

## Limitations

- Events and telemetry snapshots are synthetic registered inputs.
- Intervention requests do not execute return or hold trajectories.
- Route geometry, collision avoidance, communications, and dynamics remain unevaluated.
