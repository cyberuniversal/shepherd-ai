# Week 8 Mission Report

## Scenario

"Send two drones north to inspect crops and one drone east to inspect irrigation."

## Outcome

- Status: `completed_software_simulation_evaluation`
- Simulated assignments: `3`
- Safety validator status: `approved`
- Telemetry records: `43`

## Roadmap Metrics

- `intent_extraction_accuracy`: `0.5` (denominator `2`); exact structured-intent match across the two fixed roadmap clauses
- `grounding_accuracy`: `1.0` (denominator `2`); resolved destination match against the fixed scenario and operator resolution
- `scheduling_quality`: `1.0` (denominator `3`); task assignment completion ratio; assigned requested task replicas / total replicas
- `detection_performance`: `0.023561720474907635` (denominator `6`); mission_class_modified_mean_iou
- `overall_execution_time`: `31.334267820000434` seconds (denominator `1`); sum of measured warm-model ASR, intent, mission preparation, deterministic simulation, and vision inference wall-clock durations; model loading and notebook orchestration overhead excluded

## Limits

- Software simulation only; no physical drones were controlled.
- Safety checks validate configured rules and do not guarantee real-world safety.
- The two-clause scenario is development evidence, not a statistical end-to-end benchmark.
- Agriculture-Vision evaluation uses a disjoint internal validation remainder, not hidden test labels.
