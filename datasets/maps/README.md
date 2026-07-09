# Map Datasets

Store custom CSV or GeoJSON map datasets here.

Each dataset must document:

- source and author,
- coordinate system,
- region naming conventions,
- license or permission notes,
- train/validation/test split if used for evaluation,
- preprocessing steps.

The roadmap sample map is only an example. Do not treat it as a real evaluated dataset unless it is explicitly added with provenance.

## Current Development Map

`shepherd_test_map_v1.csv` is a synthetic/custom Week 3 development map for early grounding work. It is not a real farm, campus, airport, or public benchmark. Coordinates are WGS84 latitude/longitude values chosen for simulation consistency only.

`shepherd_test_map_v1.geojson` is a small GeoJSON representation subset of the same synthetic map. The current loader supports GeoJSON `FeatureCollection` files containing `Point` features with `radius_m` properties.

`shepherd_test_map_regions_v1.geojson` is a synthetic GeoJSON region fixture for Week 3 polygon support. It contains basic `Polygon` exterior rings plus a Point base record. The loader computes a center point and approximate radius from polygon vertices and preserves the exterior boundary for visualization. Polygon holes, multipolygons, and route/safety geometry are not implemented.

Required columns:

- `id`: stable location identifier.
- `name`: human-readable map location name.
- `category`: coarse location type.
- `latitude` and `longitude`: WGS84 coordinates for the simulated location center.
- `radius_m`: approximate region radius in meters.
- `geometry_type`: currently `circle`; future geometry types are not implemented yet.
- `map_role`: operational role such as `mission_area`, `inspection_target`, `corridor`, `base`, `restricted_area`, or `obstacle`.
- `flyable`: `true` or `false`, used as map metadata for later safety/planning modules.
- `requires_clearance`: `true` or `false`, used to flag map records that need explicit safety handling later.
- `aliases`: pipe-separated exact phrases that may refer to the location.
- `source`: provenance label.
- `split`: development/evaluation split label.

`grounding_examples_v1.jsonl` is a synthetic development smoke-check set for grounding behavior. It is not a research benchmark and must not be reported as real-world grounding accuracy.

`grounding_diagnostics_v1.jsonl` is a synthetic diagnostic set for expected failure modes such as ambiguous phrases, missing location fields, and object targets that are not map places. It is not held-out research evidence.

`grounding_holdout_synthetic_v1.jsonl` is a synthetic holdout-style evaluation split for Week 3. It contains 20 labeled commands over the same synthetic map and covers known aliases, ambiguous road references, unresolved object targets, restricted-area metadata, obstacle metadata, and map references inside constraints. It is not human-collected data and must not be reported as real-world grounding accuracy.

The current human-grounding collection packet lives under `reports/`, not this dataset directory:

- `reports/week3_human_grounding_packet.jsonl`
- `reports/week3_human_grounding_packet.md`

Those files began as collection scaffolds. The current filled packet has been finalized as `human_grounding_benchmark_v1.jsonl` with `scripts/finalize_week3_human_grounding_packet.py`. It uses `human_written_grounding_benchmark` provenance and passes `scripts/validate_grounding_dataset.py`.

`human_grounding_benchmark_v1.jsonl` is human-written command evidence over the custom synthetic map. It is not real-world map evidence.

Ambiguous or unknown map phrases must not be guessed. Grounding code should return explicit `ambiguous` or `unresolved` statuses so later planner/safety modules can request clarification or reject the mission.

The `flyable` and `requires_clearance` fields are map metadata only. They are not a complete safety validator and do not prove that a mission is safe.
