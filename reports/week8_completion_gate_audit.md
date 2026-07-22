# Week 8 Completion Gate Audit

This audit checks the fixed roadmap scenario. A completed movement simulation alone is insufficient.

## Decision

- Completion allowed: `true`
- Decision: `week8_complete_for_advancement_to_week9_paper_draft`

## Gates

- `fixed_scenario_preserved`: `true`; source_text='Send two drones north to inspect crops and one drone east to inspect irrigation.'
- `two_clauses_and_three_drones`: `true`; clauses=2, requested_drones=3
- `three_drone_schedule_and_safety`: `true`; assignments=3, safety_status='approved'
- `software_simulation_completed`: `true`; simulator='deterministic_2d_mission_simulator_v1', status='completed', telemetry_records=43
- `exact_scenario_asr_evidence`: `true`; audio_type='human_recorded_audio', audio_hash_present=True, prediction_present=True
- `trained_two_clause_intent_evaluation`: `true`; model_role='frozen_trained_checkpoint', records=2, accuracy=0.5
- `mission_assigned_vision_evaluation`: `true`; records=59, clauses=['clause_001', 'clause_002'], labeled=59, metric=0.023561720474907635
- `all_roadmap_metrics_reported`: `true`; reported=['detection_performance', 'grounding_accuracy', 'intent_extraction_accuracy', 'overall_execution_time', 'scheduling_quality'], required=['intent_extraction_accuracy', 'grounding_accuracy', 'scheduling_quality', 'detection_performance', 'overall_execution_time']
- `raw_and_derived_artifacts_present`: `true`; artifacts={'animated_map': True, 'demonstration_log': True, 'demonstration_screenshot': True, 'evaluation_summary': True, 'mission_report': True, 'raw_run': True, 'telemetry': True}
- `claim_limits_preserved`: `true`; physical=False, guarantee=False, novelty=False

## Blockers

- None
