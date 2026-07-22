# Week 8 Completion Gate Audit

This audit checks the fixed roadmap scenario. A completed movement simulation alone is insufficient.

## Decision

- Completion allowed: `false`
- Decision: `remain_on_week8_until_end_to_end_evidence_is_complete`

## Gates

- `fixed_scenario_preserved`: `true`; source_text='Send two drones north to inspect crops and one drone east to inspect irrigation.'
- `two_clauses_and_three_drones`: `true`; clauses=2, requested_drones=3
- `three_drone_schedule_and_safety`: `true`; assignments=3, safety_status='approved'
- `software_simulation_completed`: `true`; simulator='deterministic_2d_mission_simulator_v1', status='completed', telemetry_records=43
- `exact_scenario_asr_evidence`: `false`; audio_type=None, audio_hash_present=False, prediction_present=False
- `trained_two_clause_intent_evaluation`: `true`; model_role='frozen_trained_checkpoint', records=2, accuracy=0.5
- `mission_assigned_vision_evaluation`: `false`; records=None, clauses=None, labeled=None, metric=None
- `all_roadmap_metrics_reported`: `false`; reported=[], required=['intent_extraction_accuracy', 'grounding_accuracy', 'scheduling_quality', 'detection_performance', 'overall_execution_time']
- `raw_and_derived_artifacts_present`: `false`; artifacts={'animated_map': True, 'demonstration_log': False, 'demonstration_screenshot': True, 'evaluation_summary': False, 'mission_report': False, 'raw_run': True, 'telemetry': True}
- `claim_limits_preserved`: `false`; physical=None, guarantee=None, novelty=None

## Blockers

- `exact_scenario_asr_evidence`
- `mission_assigned_vision_evaluation`
- `all_roadmap_metrics_reported`
- `raw_and_derived_artifacts_present`
- `claim_limits_preserved`
