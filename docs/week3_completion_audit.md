# Week 3 Completion Audit

## Purpose

This audit exists because Week 3 must be completed in depth before Shepherd-AI moves to Week 4. The roadmap defines Week 3 as command grounding and map representation. The literature review says grounding should use explicit map data, preserve ambiguity, and avoid silent guessing.

## Current Week 3 Assets

Implemented:

- CSV map dataset: `datasets/maps/shepherd_test_map_v1.csv`
- GeoJSON Point-feature subset: `datasets/maps/shepherd_test_map_v1.geojson`
- GeoJSON region fixture: `datasets/maps/shepherd_test_map_regions_v1.geojson`
- Synthetic grounding examples: `datasets/maps/grounding_examples_v1.jsonl`
- Synthetic diagnostic examples: `datasets/maps/grounding_diagnostics_v1.jsonl`
- Synthetic holdout-style examples: `datasets/maps/grounding_holdout_synthetic_v1.jsonl`
- Grounding module: `src/shepherd_ai/grounding.py`
- Grounding dataset validation module: `src/shepherd_ai/grounding_dataset.py`
- Grounding coverage module: `src/shepherd_ai/grounding_coverage.py`
- Completion-gate audit module: `src/shepherd_ai/week3_completion.py`
- Human grounding benchmark packet module: `src/shepherd_ai/week3_human_benchmark.py`
- Synthetic acceptance criteria: `docs/week3_acceptance_criteria.md` and `docs/week3_acceptance_criteria.json`
- Research deferrals: `docs/week3_research_deferrals.md` and `docs/week3_research_deferrals.json`
- Human grounding benchmark protocol: `docs/week3_human_grounding_benchmark_protocol.md`
- Clarification module: `src/shepherd_ai/grounding_clarification.py`
- Map validation module: `src/shepherd_ai/map_validation.py`
- Map visualization module: `src/shepherd_ai/map_visualization.py`
- Week 3 status module: `src/shepherd_ai/week3_status.py`
- Colab notebook: `notebooks/Notebook3_Grounding.ipynb`

Generated outputs:

- `outputs/evaluations/grounding_examples_v1.json`
- `outputs/evaluations/grounding_diagnostics_v1.json`
- `outputs/evaluations/grounding_holdout_synthetic_v1.json`
- `outputs/evaluations/grounding_examples_v1_validation.json`
- `outputs/evaluations/grounding_diagnostics_v1_validation.json`
- `outputs/evaluations/grounding_holdout_synthetic_v1_validation.json`
- `outputs/evaluations/grounding_map_coverage_v1.json`
- `outputs/evaluations/week3_completion_gate_audit.json`
- `outputs/evaluations/grounded_intent_example.json`
- `outputs/evaluations/grounded_intent_constraint_example.json`
- `outputs/evaluations/grounded_intent_geojson_example.json`
- `outputs/evaluations/grounded_intent_polygon_example.json`
- `outputs/evaluations/map_validation_shepherd_test_map_v1.json`
- `outputs/evaluations/map_validation_shepherd_test_map_v1_geojson.json`
- `outputs/evaluations/map_validation_shepherd_test_map_regions_v1.json`
- `outputs/evaluations/grounding_clarification_ambiguous_road.json`
- `outputs/evaluations/grounding_clarification_unresolved_pickup.json`
- `outputs/evaluations/grounding_resolution_ambiguous_road_service_road.json`
- `reports/week3_map_validation_report.md`
- `reports/week3_geojson_map_validation_report.md`
- `reports/week3_region_geojson_map_validation_report.md`
- `reports/week3_grounding_map_coverage.md`
- `reports/week3_completion_gate_audit.md`
- `reports/week3_grounding_status.md`
- `reports/week3_human_grounding_packet.jsonl`
- `reports/week3_human_grounding_packet.md`
- `datasets/maps/human_grounding_benchmark_v1.jsonl`
- `outputs/evaluations/human_grounding_benchmark_v1_validation.json`
- `outputs/evaluations/human_grounding_benchmark_v1.json`

## Roadmap Coverage

Completed for Week 3:

- Explicit custom map data exists.
- Human terms can be grounded into documented coordinates.
- CSV map loading is implemented.
- Limited GeoJSON Point-feature loading is implemented.
- Basic GeoJSON Polygon exterior-ring loading is implemented.
- Folium map visualization is implemented.
- Known terms are tested.
- Ambiguous and missing terms are handled explicitly.
- Map references inside parsed constraints are surfaced as explicit grounding references.
- Grounding evaluation datasets have a validator for IDs, splits, provenance, expected statuses, map IDs, and ambiguous candidate IDs.
- Current synthetic grounding datasets cover all 20 records in the main synthetic map at least once.
- A completion-gate audit now separates synthetic roadmap gates from research gates.
- Synthetic Week 3 acceptance thresholds are now defined and checked.
- Real/public map provenance is explicitly deferred for Week 3.
- A human-grounding benchmark collection protocol and blank packet now exist.
- Raw evaluation outputs are written separately from analysis.

Partially complete:

- Evaluation exists only on synthetic development, diagnostic, and synthetic holdout-style examples.
- Label validation exists only for the current synthetic grounding datasets.
- Map coverage exists only for the current synthetic map and synthetic grounding labels.
- Completion-gate advancement remains blocked by unresolved research gates.
- The human-written grounding benchmark exists over the custom synthetic map and has validation/evaluation artifacts.
- GeoJSON polygon support is basic: exterior rings are loaded and rendered, but holes, multipolygons, and route/safety geometry are not implemented.
- Clarification requests and applied choices exist, but there is no interactive dialogue loop.

Not complete:

- No real grounding benchmark exists.
- No real-world or human-collected grounding acceptance threshold exists.
- No comparison against semantic-map, retrieval, or learned grounding methods exists.
- No real map-area provenance beyond synthetic/custom development data exists; this is explicitly deferred for Week 3.

## Literature-Driven Status

Satisfied:

- Uses explicit map data first.
- Returns structured grounding records with statuses, confidence, candidates, and notes.
- Ambiguous terms trigger failure/clarification instead of silent guessing.
- Grounding outputs preserve source intent metadata.

Still missing:

- Evidence that grounding generalizes beyond synthetic aliases.
- Semantic-map or retrieval comparison is not implemented.
- Real-world grounding accuracy is not evaluated.

## Decision

Week 3 is complete enough to move to Week 4 under the current custom-synthetic-map scope.

The current implementation is a stronger Week 3 development slice, including a larger synthetic holdout-style split, basic GeoJSON polygon support, dataset validation, map coverage, synthetic acceptance criteria, explicit real/public map deferral, a completion-gate audit, and a filled human-written grounding benchmark over the custom synthetic map. The completion gate now allows advancement. The required caveat is that this is not real-world map grounding evidence.

## Next Week 3 Work

1. Preserve the current human benchmark artifacts as Week 3 evidence.
2. Carry unresolved map limitations into Week 4 planning: holes, multipolygons, route/safety geometry, and real/public map provenance remain out of scope for the Week 3 synthetic gate.
3. Begin Week 4 only from grounded, validated map objects and do not treat real-world safety or routing as solved.
