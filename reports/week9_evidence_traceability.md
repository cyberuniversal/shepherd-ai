# Week 9 Paper Evidence Traceability

Week 8 decision: `week8_complete_for_advancement_to_week9_paper_draft`.

| Metric | Value | Denominator | Unit | Source |
|---|---:|---:|---|---|
| `intent_extraction_accuracy` | 0.5 | 2 | ratio | `outputs/evaluations/week8_exact_scenario_intent_evaluation.json` |
| `grounding_accuracy` | 1 | 2 | ratio | `outputs/evaluations/week8_roadmap_scenario_simulation.json` |
| `scheduling_quality` | 1 | 3 | ratio | `outputs/evaluations/week8_roadmap_scenario_simulation.json` |
| `detection_performance` | 0.02356172 | 6 | ratio | `outputs/evaluations/week8_mission_vision_evaluation.json` |
| `overall_execution_time` | 31.334268 | 1 | seconds | `outputs/evaluations/week8_end_to_end_evaluation.json` |

## Claim Limits

- `physical_flight_claimed`: `false`
- `safety_guarantee_claimed`: `false`
- `novelty_claimed`: `false`

## Limitations

- Software simulation only; no physical drones were controlled.
- Safety checks validate configured rules and do not guarantee real-world safety.
- The two-clause scenario is development evidence, not a statistical end-to-end benchmark.
- Agriculture-Vision evaluation uses a disjoint internal validation remainder, not hidden test labels.
