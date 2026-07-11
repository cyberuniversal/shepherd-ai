# Week 3 Grounding

## Scope

Week 3 starts the roadmap item "Command Grounding and Map Representation." The current implementation maps bounded Week 2 intent JSON fields into explicit map records and renders a Folium HTML map for inspection. It does not do semantic-map learning, image-text retrieval, route planning, or safety validation.

## Why This Comes Next

Week 2 now has a provisional handoff for typed or transcribed command intent JSON through `deterministic_v3`. Week 3 must turn location-like terms such as `north`, `greenhouse`, `irrigation canal`, or `control tent` into concrete map records before the planner can build task steps.

This supports the system requirement that later planning and scheduling modules consume bounded, inspectable structures rather than free text.

## Literature-Driven Rules

The literature review warns that language grounding is difficult and should not be treated as solved by demos alone. For this milestone, Shepherd-AI therefore uses explicit map data first and returns structured `grounded`, `ambiguous`, `unresolved`, or `not_provided` statuses.

The current grounder uses normalized map names and aliases, including embedded matches inside bounded intent fields. It does not silently pick a location for unknown or ambiguous phrases.

## Data

Current map dataset:

- `datasets/maps/shepherd_test_map_v1.csv`
- `datasets/maps/shepherd_test_map_v1.geojson`
- `datasets/maps/shepherd_test_map_regions_v1.geojson`
- Data type: synthetic/custom development map
- Coordinate system: WGS84 latitude/longitude
- Provenance label: `custom_week3_synthetic_map_v1`
- Status: development-only, not a real-world map or public benchmark
- Current geometry support: circular regions from CSV/GeoJSON Point features and basic GeoJSON Polygon exterior rings
- Current operational metadata: `map_role`, `flyable`, and `requires_clearance`

Current development examples:

- `datasets/maps/grounding_examples_v1.jsonl`
- Data type: synthetic grounding examples
- Status: smoke-check set, not a research benchmark

Current diagnostic examples:

- `datasets/maps/grounding_diagnostics_v1.jsonl`
- Data type: synthetic grounding diagnostics
- Status: expected failure-mode checks, not a held-out benchmark

Current synthetic holdout-style examples:

- `datasets/maps/grounding_holdout_synthetic_v1.jsonl`
- Data type: synthetic grounding evaluation examples
- Status: larger synthetic split for regression and coverage, not human-collected or real-world benchmark data
- Coverage: known aliases, ambiguous road references, unresolved object targets, restricted-area metadata, obstacle metadata, and map references inside constraints

Current human-collection scaffold:

- `reports/week3_human_grounding_packet.jsonl`
- `reports/week3_human_grounding_packet.md`
- Protocol: `docs/week3_human_grounding_benchmark_protocol.md`
- Finalized dataset: `datasets/maps/human_grounding_benchmark_v1.jsonl`
- Data type: human-written grounding benchmark over the custom synthetic map
- Status: filled, finalized, validated, and evaluated
- Coverage target: one slot per main synthetic map record, one ambiguous `road` slot, and one unresolved-object slot

## Interface

Primary module:

- `src/shepherd_ai/grounding.py`
- `src/shepherd_ai/grounding_dataset.py`
- `src/shepherd_ai/grounding_coverage.py`
- `src/shepherd_ai/grounding_clarification.py`
- `src/shepherd_ai/map_visualization.py`
- `src/shepherd_ai/map_validation.py`
- `src/shepherd_ai/week3_completion.py`
- `src/shepherd_ai/week3_human_benchmark.py`

Main data structures:

- `MapLocation`: one map location record with id, name, category, coordinates, radius, aliases, source, and split.
- `GroundedReference`: grounding result for one intent field, including status, selected location, candidate locations, confidence, and notes.
- `GroundedIntent`: original intent dictionary plus grounding references, readiness flag, and issues.
- `GroundedMapObject`: planner-facing map object extracted from grounded references, including center coordinates, radius, role, flyability, and clearance metadata.
- `ClarificationReport`: operator-facing questions for ambiguous or unresolved grounding results.

Primary functions:

- `load_map_locations(path)`
- `ground_phrase(phrase, locations, field_name="location")`
- `ground_intent(intent, locations)`
- `grounded_map_objects(grounded_intent)`
- `build_clarification_report(grounded_intent)`
- `render_map(locations, output_path, grounded_intent=None)`
- `validate_map_locations(locations)`

## Reproducible Example

Ground one command:

Validate the map dataset before grounding:

```powershell
python scripts/validate_map_dataset.py --map datasets/maps/shepherd_test_map_v1.csv --json-output outputs/evaluations/map_validation_shepherd_test_map_v1.json --markdown-output reports/week3_map_validation_report.md
```

Validate the synthetic region GeoJSON map:

```powershell
python scripts/validate_map_dataset.py --map datasets/maps/shepherd_test_map_regions_v1.geojson --json-output outputs/evaluations/map_validation_shepherd_test_map_regions_v1.json --markdown-output reports/week3_region_geojson_map_validation_report.md
```

Ground one command:

```powershell
python scripts/ground_intent.py --command "Send two drones north and inspect the crops." --map datasets/maps/shepherd_test_map_v1.csv --output outputs/evaluations/grounded_intent_example.json
```

Create an explicit clarification report for an ambiguous command:

```powershell
python scripts/create_grounding_clarification_report.py --command "Monitor the road until the ambulance arrives." --map datasets/maps/shepherd_test_map_v1.csv --output outputs/evaluations/grounding_clarification_ambiguous_road.json
```

Apply explicit operator choices to resolve an ambiguous grounding artifact:

```powershell
python scripts/apply_grounding_clarification.py --grounded-json outputs/evaluations/grounding_clarification_ambiguous_road.json --map datasets/maps/shepherd_test_map_v1.csv --choice location=loc_service_road --choice target=loc_service_road --output outputs/evaluations/grounding_resolution_ambiguous_road_service_road.json
```

Summarize the current Week 3 grounding state:

```powershell
python scripts/summarize_week3_grounding_status.py --map-validation outputs/evaluations/map_validation_shepherd_test_map_v1.json --grounding-evaluation outputs/evaluations/grounding_examples_v1.json --grounding-evaluation outputs/evaluations/grounding_diagnostics_v1.json --clarification-report outputs/evaluations/grounding_clarification_ambiguous_road.json --clarification-report outputs/evaluations/grounding_clarification_unresolved_pickup.json --applied-resolution outputs/evaluations/grounding_resolution_ambiguous_road_service_road.json --output-json outputs/evaluations/week3_grounding_status.json --output-markdown reports/week3_grounding_status.md
```

Create an explicit clarification report for an unresolved command:

```powershell
python scripts/create_grounding_clarification_report.py --command "Capture images of the red pickup truck." --map datasets/maps/shepherd_test_map_v1.csv --output outputs/evaluations/grounding_clarification_unresolved_pickup.json
```

Run the development smoke evaluation:

```powershell
python scripts/evaluate_grounding.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/grounding_examples_v1.jsonl --output outputs/evaluations/grounding_examples_v1.json
```

Validate the development smoke dataset labels:

```powershell
python scripts/validate_grounding_dataset.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/grounding_examples_v1.jsonl --summary-output outputs/evaluations/grounding_examples_v1_validation.json
```

Render a Folium HTML map with grounded references highlighted:

```powershell
python scripts/render_grounding_map.py --map datasets/maps/shepherd_test_map_v1.csv --command "Send two drones north and inspect the crops." --output outputs/maps/shepherd_test_map_v1_grounded_example.html
```

Run the diagnostic failure-mode evaluation:

```powershell
python scripts/evaluate_grounding.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/grounding_diagnostics_v1.jsonl --output outputs/evaluations/grounding_diagnostics_v1.json
```

Validate the diagnostic failure-mode labels:

```powershell
python scripts/validate_grounding_dataset.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/grounding_diagnostics_v1.jsonl --summary-output outputs/evaluations/grounding_diagnostics_v1_validation.json
```

Run the synthetic holdout-style evaluation:

```powershell
python scripts/evaluate_grounding.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/grounding_holdout_synthetic_v1.jsonl --output outputs/evaluations/grounding_holdout_synthetic_v1.json
```

Validate the synthetic holdout-style labels:

```powershell
python scripts/validate_grounding_dataset.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/grounding_holdout_synthetic_v1.jsonl --summary-output outputs/evaluations/grounding_holdout_synthetic_v1_validation.json
```

Audit synthetic map coverage across all current grounding datasets:

```powershell
python scripts/audit_grounding_coverage.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/grounding_examples_v1.jsonl --dataset datasets/maps/grounding_diagnostics_v1.jsonl --dataset datasets/maps/grounding_holdout_synthetic_v1.jsonl --json-output outputs/evaluations/grounding_map_coverage_v1.json --markdown-output reports/week3_grounding_map_coverage.md
```

Audit Week 3 completion gates:

```powershell
python scripts/audit_week3_completion.py --map-validation outputs/evaluations/map_validation_shepherd_test_map_v1.json --region-map-validation outputs/evaluations/map_validation_shepherd_test_map_regions_v1.json --grounding-evaluation outputs/evaluations/grounding_examples_v1.json --grounding-evaluation outputs/evaluations/grounding_diagnostics_v1.json --grounding-evaluation outputs/evaluations/grounding_holdout_synthetic_v1.json --grounding-dataset-validation outputs/evaluations/grounding_examples_v1_validation.json --grounding-dataset-validation outputs/evaluations/grounding_diagnostics_v1_validation.json --grounding-dataset-validation outputs/evaluations/grounding_holdout_synthetic_v1_validation.json --coverage-report outputs/evaluations/grounding_map_coverage_v1.json --week3-status outputs/evaluations/week3_grounding_status.json --acceptance-criteria docs/week3_acceptance_criteria.json --research-deferrals docs/week3_research_deferrals.json --json-output outputs/evaluations/week3_completion_gate_audit.json --markdown-output reports/week3_completion_gate_audit.md
```

Create the blank human grounding benchmark collection packet:

```powershell
python scripts/create_week3_human_grounding_packet.py --map datasets/maps/shepherd_test_map_v1.csv --jsonl-output reports/week3_human_grounding_packet.jsonl --markdown-output reports/week3_human_grounding_packet.md
```

The packet above is not evidence. It only gives a fast, controlled way to collect human-written commands for the remaining Week 3 blocker.

After a human fills every slot, finalize the packet into a dataset:

```powershell
python scripts/finalize_week3_human_grounding_packet.py --packet reports/week3_human_grounding_packet.jsonl --output datasets/maps/human_grounding_benchmark_v1.jsonl
```

The finalizer fails if any slot is still blank. The finalized dataset must still pass `validate_grounding_dataset.py` and `evaluate_grounding.py`, and those outputs must be passed to `audit_week3_completion.py` through `--human-grounding-dataset-validation` and `--human-grounding-evaluation`.

Create a constraint-grounding example:

```powershell
python scripts/ground_intent.py --command "Inspect the greenhouse and avoid the power lines." --map datasets/maps/shepherd_test_map_v1.csv --output outputs/evaluations/grounded_intent_constraint_example.json
```

Create a polygon-grounding example:

```powershell
python scripts/ground_intent.py --command "Inspect the polygon zone." --map datasets/maps/shepherd_test_map_regions_v1.geojson --output outputs/evaluations/grounded_intent_polygon_example.json
```

Render an ambiguous grounding example:

```powershell
python scripts/render_grounding_map.py --map datasets/maps/shepherd_test_map_v1.csv --command "Monitor the road until the ambulance arrives." --output outputs/maps/shepherd_test_map_v1_ambiguous_road.html
```

Render a restricted-area metadata example:

```powershell
python scripts/render_grounding_map.py --map datasets/maps/shepherd_test_map_v1.csv --command "Inspect the restricted area." --output outputs/maps/shepherd_test_map_v1_restricted_area.html
```

Render a polygon GeoJSON example:

```powershell
python scripts/render_grounding_map.py --map datasets/maps/shepherd_test_map_regions_v1.geojson --command "Inspect the polygon zone." --output outputs/maps/shepherd_test_map_regions_v1_polygon_example.html
```

Current development smoke-check result:

- Records: 6
- Exact record matches: 6
- Exact record accuracy: 1.0
- Reference matches: 12 / 12
- Reference accuracy: 1.0

Current diagnostic result:

- Records: 5
- Exact record matches: 5
- Exact record accuracy: 1.0
- Reference matches: 10 / 10
- Reference accuracy: 1.0
- Label-validation result: 5 records, 2 ambiguous references, 3 unresolved references, and the expected ambiguous `road` candidates are explicitly recorded.

Current synthetic holdout-style result:

- Records: 20
- Exact record matches: 20
- Exact record accuracy: 1.0
- Reference matches: 44 / 44
- Reference accuracy: 1.0
- Required caveat: this is a synthetic split over the same custom development map, not a real-world grounding benchmark.
- Label-validation result: 20 records, 1 ambiguous reference, 6 unresolved references, and 17 unique grounded map IDs.

Current synthetic map coverage result:

- Dataset records: 31
- Expected references: 66
- Covered map records: 20 / 20
- Covered roles: base, corridor, inspection_target, mission_area, obstacle, and restricted_area
- Untested map records: 0
- Warnings: 0
- Required caveat: this only proves coverage of the current synthetic map labels, not real-world grounding performance.

Current Week 3 completion-gate result:

- Roadmap gates passed: true
- Research gates passed: true
- Advancement allowed: true
- Current blocker: none.
- Synthetic acceptance criteria: defined in `docs/week3_acceptance_criteria.md` and `docs/week3_acceptance_criteria.json`.
- Real/public map provenance: explicitly deferred for Week 3 in `docs/week3_research_deferrals.md` and `docs/week3_research_deferrals.json`.
- Human benchmark protocol: defined in `docs/week3_human_grounding_benchmark_protocol.md`.
- Human benchmark dataset: `datasets/maps/human_grounding_benchmark_v1.jsonl`, validated in `outputs/evaluations/human_grounding_benchmark_v1_validation.json` and evaluated in `outputs/evaluations/human_grounding_benchmark_v1.json`.
- Required caveat: this clears the Week 3 custom-map grounding gate, but it does not prove real-world map grounding.

These results are only for the synthetic development and diagnostic examples above. They are not evidence of real-world map grounding performance.

Current map validation result:

- Records: 20
- Restricted records: 1
- Obstacle records: 1
- Warnings: 1
- Warning: ambiguous map terms require clarification before planning

Current synthetic region GeoJSON validation result:

- Records: 3
- Geometry types: 2 polygon records and 1 circle record
- Restricted records: 1
- Obstacle records: 0
- Warnings: 0

Current clarification examples:

- `Monitor the road until the ambulance arrives.` produces 2 clarification requests and blocks planning because `road` maps to both `loc_service_road` and `loc_main_road`.
- `Capture images of the red pickup truck.` produces 1 clarification request and blocks planning because no map record matches `red pickup truck`.
- Applying explicit choices `location=loc_service_road` and `target=loc_service_road` resolves the ambiguous-road artifact, leaves 0 clarification requests, and preserves the original command text.
- `Inspect the greenhouse and avoid the power lines.` grounds the target to `loc_greenhouse` and grounds the constraint reference to `obs_power_lines`, surfacing obstacle metadata as issues for later safety validation.
- `Inspect the polygon zone.` grounds the target to `poly_north_field`, preserving a polygon exterior boundary for visualization.

Current Week 3 status summary:

- Earlier status artifact: `reports/week3_grounding_status.md`
- Required caveat: this is a synthetic development-readiness artifact, not permission to move weeks.
- Current audit: `docs/week3_completion_audit.md`
- Current completion-gate audit: `reports/week3_completion_gate_audit.md`
- Audit decision: Week 3 is complete for advancement under the current synthetic-map scope and explicit real/public map deferral.

## Baseline

The current baseline is deterministic matching over map names and aliases after simple normalization, including embedded map terms inside bounded intent fields:

- lowercase
- punctuation removal
- whitespace normalization
- leading article removal for `the`, `a`, and `an`

No trained grounding model exists yet. No embedding retrieval, VLMaps-style semantic map, GeoText-style image-text retrieval, or LLM-based grounding is implemented.

## Evaluation

Metric for the current smoke check:

- Reference accuracy: whether each expected `location` and `target` grounding status and location id match the labeled development example.
- Exact record accuracy: whether all evaluated references in a record match.

Roadmap-level real-world grounding accuracy remains not evaluated because the repository does not yet contain a real grounding benchmark, formal real map area, or human-collected acceptance threshold. The current acceptance criteria apply only to the synthetic Week 3 gate.

Map visualization is an inspection aid, not an evaluation result. It should be used to check whether grounding records and map locations are visually plausible before planner work begins.

Map validation is an audit step, not a safety certificate. Its current purpose is to expose schema counts, role counts, ambiguous aliases, restricted records, obstacle records, and warnings before planner work begins.

## Known Limitations

- The map is synthetic and small.
- GeoJSON support currently covers Point features and basic Polygon exterior rings; holes, multipolygons, and route/safety geometry remain unimplemented.
- The examples are development examples, not a held-out benchmark.
- Matching will fail on paraphrases that do not contain a listed map name or alias.
- The module grounds intent `location`, `target`, and map references inside parsed constraint strings when a known map term is present or a map-like constraint cannot be resolved.
- Object targets such as `stalled vehicles` are reported as unresolved map references unless the map explicitly lists them.
- Ambiguous matches are blocked for planning readiness instead of guessed.
- Folium visualization is implemented for map inspection, but no route, polygon, obstacle, restricted-area, or safety visualization exists yet.
- Restricted areas and obstacles are currently represented as circular map records with metadata. They are not enforced by a safety validator yet.
- The current ambiguity examples are intentionally synthetic and do not define a final clarification dialogue policy.
- Applied clarifications are explicit operator interventions. They should not be reported as automatic grounding success.
- The map validation report does not prove route feasibility or mission safety.
- The Week 3 status summary is a development-readiness summary, not evidence that grounding is complete.
- The Week 3 completion audit does not prove real-world grounding because the map is still synthetic.
- The human grounding benchmark is human-written command data over the synthetic map. It is not a real map or public benchmark.

## Completion Criteria For This Slice

This Week 3 slice is complete when:

- map CSV loading validates required schema and duplicate ids,
- GeoJSON Point and basic Polygon feature loading validates required schema and duplicate ids,
- known aliases ground to documented map records,
- missing phrases return `not_provided`,
- unknown phrases return `unresolved`,
- ambiguous phrases return `ambiguous` with candidates,
- a typed command can be parsed and grounded from the CLI,
- a Folium map can be rendered from the explicit CSV map and optional grounded intent,
- a map validation report can summarize roles, ambiguous aliases, restricted records, obstacle records, and warnings,
- a clarification report can explain ambiguous or unresolved grounding before planning,
- explicit operator choices can be applied to produce a resolved grounded artifact without changing the original command text,
- a development grounding smoke evaluation writes raw output,
- a larger synthetic holdout-style evaluation writes raw output,
- grounding evaluation datasets validate IDs, splits, provenance, expected statuses, grounded map IDs, and ambiguous candidate IDs,
- a coverage audit confirms which synthetic map records and roles are exercised by the current labeled grounding datasets,
- a completion-gate audit separates synthetic roadmap readiness from unresolved research blockers,
- a human-written grounding benchmark exists over the custom synthetic map,
- map references inside parsed constraints are surfaced as grounded, ambiguous, or unresolved references,
- tests cover the behavior above.
