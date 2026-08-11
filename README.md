# Shepherd-AI

Shepherd-AI is a Python research prototype for natural-language multi-drone
mission planning and coordination in software simulation.

Current research direction: the original ten-week prototype and its results are
preserved, but the active paper is now a proposed systems-and-measurement study
of validation placement on paired MultiUAV-Plat source tasks. The study compares
monolithic, deterministic post-plan, stage-wise, and compute-matched post-plan
configurations while jointly measuring safety, utility, failure containment,
and local inference cost. Source acquisition, split, strict output parsing, and
standalone recursive grounding validation are implemented. The corrected
30-cluster pilot is balanced across its two supported intervention templates
and its 150 cases are structurally approved. The same construction has produced
a deterministically validated full draft of 1,473 clusters and 7,365 cases;
the 30-cluster, 150-case expert sample validates the construction templates
without claiming full row-level human labeling. A score-blind protocol and
approved 1,420-case held-out manifest are frozen. Final run configurations are
bound to the exact execution-code commit, and both no-inference cache/runtime
preflights pass. The complete 3B and 7B accuracy matrices are now preserved as
sealed checkpoints with 5,680 rows each. Both matrices passed the score-blind
publication-admission gate in
`datasets/multiuav_plat/accuracy_matrix_admission_v1.json`; no hidden labels or
study scores were accessed before that gate. Registered deterministic scoring
has now completed for all 11,360 admitted rows, with derived rows kept separate
from the aggregate summary under
`outputs/evaluations/multiuav_accuracy_scoring_v1/`. The scores are descriptive
and must be interpreted through the registered source-cluster bootstrap. That
bootstrap is complete for both primary outcomes and both registered contrasts,
with raw draws kept separate under
`outputs/evaluations/multiuav_accuracy_bootstrap_v1/`. A reusable accuracy CLI validates the commit, data,
protocol, cache, and row counts before model loading, then writes durable
resumable rows and checkpoints. The label-separated scorer is frozen and source-hashed: it
preserves raw model behavior, derives the post-gate system disposition, applies
the same external grounding validator to every method, and reads hidden
official command inventories only after complete-matrix admission. Versioned
M1-M4 prompts, a provider-independent
runner, and config-bound checkpoint/resume are also implemented with scripted
tests. The pinned Qwen 2.5 3B and 7B checkpoints are cached outside Git, fully
checksummed, and successfully loaded and invoked under the local socket guard
on synthetic fixtures only. The current smokes generated one token each and
were not interpreted as plans; the earlier 32-token 3B smoke is preserved as
historical infrastructure evidence. The 7B smoke required CPU and disk
offload on the local 4 GB GPU. A one-row local 3B feasibility attempt was
aborted after its first call required 389.9 seconds; its raw row, logs, config,
and protocol-deviation record are preserved and excluded from study results.
The registered accuracy figures and their source tables are now reproducible
under `reports/figures/` and `outputs/tables/`, with a provenance manifest at
`outputs/evaluations/multiuav_accuracy_figures_v1/manifest.json`. The approved
30-cluster resource schedule and RTX 3090 controls are frozen. Preflight v2
passed. Resource attempt 2 completed one 150-row condition, then failed before
condition 2 measurement because the GPU baseline was 68 C against the frozen
60 C ceiling. The partial raw package is preserved but is not an admitted
resource result. The cooldown-aware baseline acquisition fix passes its
regression tests, all 24 attempt-3 configs are bound to that execution revision,
and no-inference RTX 3090 preflight v3 independently passed for both frozen
models. Attempt 3 then completed all 24 conditions and 3,600 rows on one locked
RTX 3090; the complete raw archive and Kubernetes evidence are hash-preserved.
The rows remain unscored and are not resource findings until score-blind
resource admission and the registered aggregate analysis pass. See
`docs/multiuav_validation_study_protocol.md`.
The requirement-by-requirement implementation ledger is
`docs/code_plan_compliance.md`.

## Project Rule

The roadmap is used for sequence and broad scope. The literature review is used for actual technical implementation decisions.

That means Shepherd-AI should not stop at hand-written demos when the reviewed papers indicate that training, domain adaptation, deterministic validation, structured representations, or held-out evaluation are required. Baselines are allowed, but they must be labeled as baselines and compared against trained or literature-supported approaches when the data exists.

## Source Documents

The current source of truth is:

- `AGENTS.md`
- `docs/roadmap.pdf`
- `docs/literature_review/ExportBlock-44375080-06b3-45d5-a3ed-ac880ba80cd6-Part-1.zip`
- `docs/project_synthesis.md`
- `docs/implementation_plan.md`
- `docs/milestone_2_speech_input.md`
- `docs/literature_to_implementation.md`
- `docs/source_material/code_plan_2026-07-25.docx`
- `docs/code_plan_compliance.md`
- `docs/multiuav_validation_study_protocol.md`
- `docs/multiuav_agent_context_protocol.md`
- `docs/multiuav_recoverability_protocol.md`
- `docs/multiuav_intervention_pilot_protocol.md`
- `docs/multiuav_intervention_review_protocol.md`
- `docs/multiuav_intervention_dataset_protocol.md`
- `docs/multiuav_intervention_feedback_resolution.md`
- `docs/multiuav_method_contract.md`
- `docs/multiuav_grounding_validator_protocol.md`
- `docs/multiuav_model_revisions.md`
- `docs/multiuav_runner_checkpoint_protocol.md`
- `docs/multiuav_offline_runtime_protocol.md`
- `docs/multiuav_statistical_analysis_protocol.md`
- `docs/multiuav_scoring_protocol.md`
- `docs/multiuav_qwen_cache_smoke.md`
- `docs/multiuav_execution_scope_protocol.md`
- `docs/multiuav_hardware_measurement_protocol.md`
- `docs/week2_data_collection_protocol.md`
- `docs/week2_audio_split_policy.md`
- `docs/week2_training_explainer.md`
- `docs/week2_span_annotation.md`
- `docs/week3_grounding.md`
- `docs/week4_mission_planning.md`
- `docs/week4_acceptance_criteria.md`
- `docs/week4_research_deferrals.md`
- `docs/week8_protocol.md`
- `docs/week8_acceptance_criteria.json`
- `docs/roadmap_status.md`
- `docs/repository_hygiene.md`

The roadmap path is `docs/roadmap.pdf`; there is currently no `docs/roadmap/` directory.

The MultiUAV-Plat study is a post-roadmap refinement of Week 9 and Week 10, not
an additional completed roadmap milestone. The earlier Week 9 paper draft and
38-case evidence diagnostics are historical development evidence and must not
be reported as results of the new study.

## Google Colab Structure

The repository now includes the roadmap's Colab-style notebook sequence:

- `notebooks/Notebook1_Setup.ipynb`
- `notebooks/Notebook2_NLP.ipynb`
- `notebooks/Notebook3_Grounding.ipynb`
- `notebooks/Notebook4_Planner.ipynb`
- `notebooks/Notebook5_Scheduler.ipynb`
- `notebooks/Notebook6_Vision.ipynb`
- `notebooks/Notebook7_Safety.ipynb`
- `notebooks/Notebook8_FinalDemo.ipynb`
- `notebooks/Notebook9_Evaluation.ipynb`

Notebooks should orchestrate Colab workflows. Reusable implementation belongs in `src/shepherd_ai/`, with tests in `tests/`. Transformer fine-tuning is Colab-first and should use a GPU runtime, not local CPU training.

The active MultiUAV inference environment is optional:

```powershell
python -m pip install -e .[multiuav-inference]
```

That command installs runtime libraries only. It does not cache either pinned
Qwen checkpoint or start the locked experiment. Accuracy inference requires the
committed run configurations bound to the approved case manifest. The stored 3B
and 7B preflights pass. Reproduce one without loading a model using:

```powershell
.venv312\Scripts\python.exe scripts/run_multiuav_accuracy.py `
  --model-id Qwen/Qwen2.5-3B-Instruct `
  --preflight-only
```

Use the project `.venv312` environment for local Qwen execution. The system
Python may run repository tests but is not the registered inference runtime.

Dataset and artifact locations:

- `datasets/commands/`
- `datasets/sample_audio/`
- `datasets/maps/`
- `datasets/aerial_images/`
- `outputs/`
- `reports/`

GitHub hygiene: source code, tests, docs, notebooks, and small curated fixtures
are tracked. Generated `outputs/` and `reports/` are ignored by default unless a
specific artifact is deliberately promoted. See `docs/repository_hygiene.md`.
Roadmap-to-repository mapping is tracked in `docs/roadmap_status.md`.

## Week 3 Grounding

The initial grounding slice maps `deterministic_v3` intent JSON into explicit synthetic map records. It uses exact normalized map names and aliases, and returns structured `grounded`, `ambiguous`, `unresolved`, or `not_provided` statuses for location, target, and map references inside parsed constraints. It also renders a Folium HTML map for inspection. It does not use learned semantic grounding, image retrieval, routing, planning, or safety validation.

The map schema now includes circular-region metadata for `map_role`, `flyable`, and `requires_clearance`. Those fields prepare grounded records for later planner and safety modules, but they are not a safety validator.

The map loader supports CSV and a limited GeoJSON format. Current GeoJSON support covers `FeatureCollection` files containing `Point` features with `radius_m` properties and basic `Polygon` exterior rings. Polygon holes, multipolygons, and route/safety geometry are not implemented.

Run one grounding example:

Validate the map dataset:

```powershell
python scripts/validate_map_dataset.py --map datasets/maps/shepherd_test_map_v1.csv --json-output outputs/evaluations/map_validation_shepherd_test_map_v1.json --markdown-output reports/week3_map_validation_report.md
```

Validate the synthetic region GeoJSON map:

```powershell
python scripts/validate_map_dataset.py --map datasets/maps/shepherd_test_map_regions_v1.geojson --json-output outputs/evaluations/map_validation_shepherd_test_map_regions_v1.json --markdown-output reports/week3_region_geojson_map_validation_report.md
```

Run one grounding example:

```powershell
python scripts/ground_intent.py --command "Send two drones north and inspect the crops." --map datasets/maps/shepherd_test_map_v1.csv --output outputs/evaluations/grounded_intent_example.json
```

Create clarification reports for blocked grounding:

```powershell
python scripts/create_grounding_clarification_report.py --command "Monitor the road until the ambulance arrives." --map datasets/maps/shepherd_test_map_v1.csv --output outputs/evaluations/grounding_clarification_ambiguous_road.json
python scripts/create_grounding_clarification_report.py --command "Capture images of the red pickup truck." --map datasets/maps/shepherd_test_map_v1.csv --output outputs/evaluations/grounding_clarification_unresolved_pickup.json
```

Apply explicit operator choices to an ambiguous grounding artifact:

```powershell
python scripts/apply_grounding_clarification.py --grounded-json outputs/evaluations/grounding_clarification_ambiguous_road.json --map datasets/maps/shepherd_test_map_v1.csv --choice location=loc_service_road --choice target=loc_service_road --output outputs/evaluations/grounding_resolution_ambiguous_road_service_road.json
```

Summarize Week 3 grounding status:

```powershell
python scripts/summarize_week3_grounding_status.py --map-validation outputs/evaluations/map_validation_shepherd_test_map_v1.json --grounding-evaluation outputs/evaluations/grounding_examples_v1.json --grounding-evaluation outputs/evaluations/grounding_diagnostics_v1.json --grounding-evaluation outputs/evaluations/grounding_holdout_synthetic_v1.json --clarification-report outputs/evaluations/grounding_clarification_ambiguous_road.json --clarification-report outputs/evaluations/grounding_clarification_unresolved_pickup.json --applied-resolution outputs/evaluations/grounding_resolution_ambiguous_road_service_road.json --output-json outputs/evaluations/week3_grounding_status.json --output-markdown reports/week3_grounding_status.md
```

Run the synthetic development smoke evaluation:

```powershell
python scripts/evaluate_grounding.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/grounding_examples_v1.jsonl --output outputs/evaluations/grounding_examples_v1.json
```

Validate the synthetic development grounding labels:

```powershell
python scripts/validate_grounding_dataset.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/grounding_examples_v1.jsonl --summary-output outputs/evaluations/grounding_examples_v1_validation.json
```

Render the current map and highlighted grounded command:

```powershell
python scripts/render_grounding_map.py --map datasets/maps/shepherd_test_map_v1.csv --command "Send two drones north and inspect the crops." --output outputs/maps/shepherd_test_map_v1_grounded_example.html
```

Render the synthetic region GeoJSON polygon example:

```powershell
python scripts/render_grounding_map.py --map datasets/maps/shepherd_test_map_regions_v1.geojson --command "Inspect the polygon zone." --output outputs/maps/shepherd_test_map_regions_v1_polygon_example.html
```

Run the diagnostic failure-mode set:

```powershell
python scripts/evaluate_grounding.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/grounding_diagnostics_v1.jsonl --output outputs/evaluations/grounding_diagnostics_v1.json
```

Validate the diagnostic grounding labels:

```powershell
python scripts/validate_grounding_dataset.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/grounding_diagnostics_v1.jsonl --summary-output outputs/evaluations/grounding_diagnostics_v1_validation.json
```

Run the larger synthetic holdout-style set:

```powershell
python scripts/evaluate_grounding.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/grounding_holdout_synthetic_v1.jsonl --output outputs/evaluations/grounding_holdout_synthetic_v1.json
```

Validate the synthetic holdout-style grounding labels:

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

Create the blank human-collection packet for the remaining Week 3 grounding benchmark gate:

```powershell
python scripts/create_week3_human_grounding_packet.py --map datasets/maps/shepherd_test_map_v1.csv --jsonl-output reports/week3_human_grounding_packet.jsonl --markdown-output reports/week3_human_grounding_packet.md
```

This packet creates 22 blank slots: one for each main synthetic map record, one ambiguous `road` slot, and one unresolved-object slot. It is a collection worksheet only. It must not be moved into `datasets/maps/` or treated as benchmark evidence until a human fills every `text` field and the completed JSONL passes grounding-dataset validation and evaluation.

After the packet is human-filled, finalize it into a dataset:

```powershell
python scripts/finalize_week3_human_grounding_packet.py --packet reports/week3_human_grounding_packet.jsonl --output datasets/maps/human_grounding_benchmark_v1.jsonl
```

The finalizer fails on blank `text` fields and writes records with `data_type` set to `human_written_grounding_benchmark`. The resulting dataset still must be validated and evaluated before the Week 3 completion audit can accept it.

Create a constraint-grounding example:

```powershell
python scripts/ground_intent.py --command "Inspect the greenhouse and avoid the power lines." --map datasets/maps/shepherd_test_map_v1.csv --output outputs/evaluations/grounded_intent_constraint_example.json
```

Create a polygon-grounding example:

```powershell
python scripts/ground_intent.py --command "Inspect the polygon zone." --map datasets/maps/shepherd_test_map_regions_v1.geojson --output outputs/evaluations/grounded_intent_polygon_example.json
```

Current smoke-check result: 6 / 6 exact records and 12 / 12 reference matches on `datasets/maps/grounding_examples_v1.jsonl`. This is not real-world grounding accuracy; it only verifies the current synthetic map, examples, parser, and exact-alias grounder are internally consistent.

Current diagnostic result: 5 / 5 exact records and 10 / 10 reference matches on `datasets/maps/grounding_diagnostics_v1.jsonl`. This checks expected `ambiguous`, `unresolved`, `not_provided`, and restricted-area metadata behavior; it is not held-out research evidence.

Current synthetic holdout-style result: 20 / 20 exact records and 44 / 44 reference matches on `datasets/maps/grounding_holdout_synthetic_v1.jsonl`. This is still synthetic evidence over the same custom map, not real-world grounding accuracy.

Current grounding dataset validation outputs: `outputs/evaluations/grounding_examples_v1_validation.json`, `outputs/evaluations/grounding_diagnostics_v1_validation.json`, and `outputs/evaluations/grounding_holdout_synthetic_v1_validation.json`. These validate record IDs, splits, provenance fields, expected statuses, map IDs, and ambiguous candidate IDs.

Current grounding coverage output: `reports/week3_grounding_map_coverage.md` and `outputs/evaluations/grounding_map_coverage_v1.json`. Across the current synthetic development, diagnostic, and holdout-style datasets, the report shows 31 dataset records, 66 expected references, 20 / 20 synthetic map records covered, and 0 coverage warnings. This is synthetic coverage, not real-world accuracy.

Current Week 3 acceptance criteria: `docs/week3_acceptance_criteria.md` and `docs/week3_acceptance_criteria.json`. These define the synthetic Week 3 gate only; they are not real-world grounding thresholds.

Current Week 3 deferrals: `docs/week3_research_deferrals.md` and `docs/week3_research_deferrals.json`. Real/public map provenance is explicitly deferred for Week 3 because the roadmap uses a custom simulation map; this does not permit real-world grounding claims.

Current Week 3 human benchmark protocol: `docs/week3_human_grounding_benchmark_protocol.md`. The filled packet is `reports/week3_human_grounding_packet.jsonl` and `reports/week3_human_grounding_packet.md`; the finalized benchmark dataset is `datasets/maps/human_grounding_benchmark_v1.jsonl`.

Current Week 3 human benchmark outputs: `outputs/evaluations/human_grounding_benchmark_v1_validation.json` and `outputs/evaluations/human_grounding_benchmark_v1.json`. Current result: 22 / 22 exact records and 22 / 22 reference matches. This is human-written command evidence over the custom synthetic map, not real-world map evidence.

Current Week 3 completion-gate output: `reports/week3_completion_gate_audit.md` and `outputs/evaluations/week3_completion_gate_audit.json`. The synthetic roadmap gates, synthetic acceptance thresholds, real/public map deferral, and human-written grounding benchmark gate now pass; advancement is currently `true`.

Current map-rendering outputs include `outputs/maps/shepherd_test_map_v1_grounded_example.html`, `outputs/maps/shepherd_test_map_v1_ambiguous_road.html`, and `outputs/maps/shepherd_test_map_v1_restricted_area.html`. These are inspection artifacts, not evaluation metrics.

Current map validation output: `reports/week3_map_validation_report.md` and `outputs/evaluations/map_validation_shepherd_test_map_v1.json`. The report currently shows 20 map records, 1 restricted record, 1 obstacle record, and 1 expected warning for ambiguous aliases.

Current synthetic region GeoJSON validation output: `reports/week3_region_geojson_map_validation_report.md` and `outputs/evaluations/map_validation_shepherd_test_map_regions_v1.json`. The report currently shows 3 map records, 2 polygon records, 1 circle record, 1 restricted record, and 0 warnings.

Current clarification outputs: `outputs/evaluations/grounding_clarification_ambiguous_road.json` and `outputs/evaluations/grounding_clarification_unresolved_pickup.json`. These are operator-facing review artifacts, not planner execution.

Current applied-clarification output: `outputs/evaluations/grounding_resolution_ambiguous_road_service_road.json`. This records explicit operator choices and preserves the original command text.

Current Week 3 status output: `reports/week3_grounding_status.md` and `outputs/evaluations/week3_grounding_status.json`. It is now treated as a synthetic development-readiness artifact, not permission to move weeks.

Current Week 3 completion audit: `docs/week3_completion_audit.md`. The audit says Week 3 is complete enough to move to Week 4 under the current custom synthetic-map scope.

## Week 4 Mission Planning

The initial Week 4 slice converts grounded Week 3 outputs into inspectable task sequences and explicit NetworkX-backed dependency graphs. It is deterministic and does not schedule drones, optimize routes, execute simulation, run the actual Week 6 vision model, or validate safety. Observation commands explicitly include the roadmap sequence: takeoff, fly-to, capture images, plan a downstream vision-model task, save results, and return. Commands with grounded constraints include a `review_constraints` step before takeoff, and restricted or clearance-related map metadata is preserved as planner issues for later safety work.

Plan one command:

```powershell
python scripts/plan_mission.py --command "Scan the crops in the north field." --map datasets/maps/shepherd_test_map_v1.csv --output outputs/evaluations/week4_plan_north_field_example.json
```

Create a blocked plan for ambiguous grounding:

```powershell
python scripts/plan_mission.py --command "Check if there is any traffic on the road." --map datasets/maps/shepherd_test_map_v1.csv --output outputs/evaluations/week4_plan_ambiguous_road_blocked.json
```

Create a constrained plan that carries obstacle metadata forward:

```powershell
python scripts/plan_mission.py --command "Inspect the greenhouse and avoid the power lines." --map datasets/maps/shepherd_test_map_v1.csv --output outputs/evaluations/week4_plan_constraint_greenhouse_power_lines.json
```

Evaluate the planner over the human-written Week 3 grounding benchmark:

```powershell
python scripts/evaluate_mission_planning.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/human_grounding_benchmark_v1.jsonl --output outputs/evaluations/week4_planning_human_grounding_benchmark_v1.json
```

Evaluate focused Week 4 planning cases:

```powershell
python scripts/evaluate_mission_planning.py --map datasets/maps/shepherd_test_map_v1.csv --dataset datasets/maps/week4_planning_cases_v1.jsonl --output outputs/evaluations/week4_planning_cases_v1.json
```

Render a mission-flow diagram:

```powershell
python scripts/render_mission_flow.py --command "Scan the crops in the north field." --map datasets/maps/shepherd_test_map_v1.csv --output outputs/diagrams/week4_plan_north_field_flow.md
```

Audit Week 4 completion gates:

```powershell
python scripts/audit_week4_completion.py --human-planning-evaluation outputs/evaluations/week4_planning_human_grounding_benchmark_v1.json --focused-planning-evaluation outputs/evaluations/week4_planning_cases_v1.json --flow-diagram outputs/diagrams/week4_plan_north_field_flow.md --acceptance-criteria docs/week4_acceptance_criteria.json --research-deferrals docs/week4_research_deferrals.json --json-output outputs/evaluations/week4_completion_gate_audit.json --markdown-output reports/week4_completion_gate_audit.md
```

Current Week 4 planning output:

- Example plan: `outputs/evaluations/week4_plan_north_field_example.json`
- Blocked ambiguous-road plan: `outputs/evaluations/week4_plan_ambiguous_road_blocked.json`
- Constraint example plan: `outputs/evaluations/week4_plan_constraint_greenhouse_power_lines.json`
- Mission-flow diagram: `outputs/diagrams/week4_plan_north_field_flow.md`
- Planning evaluation: `outputs/evaluations/week4_planning_human_grounding_benchmark_v1.json`
- Focused planning-case evaluation: `outputs/evaluations/week4_planning_cases_v1.json`
- Completion gate audit: `outputs/evaluations/week4_completion_gate_audit.json` and `reports/week4_completion_gate_audit.md`
- Human grounding benchmark result: 22 records, 20 planned, 2 blocked, 22 / 22 expected plan-status matches, 22 / 22 required action matches, 22 / 22 required issue matches, and 22 / 22 valid plan contracts.
- Focused planning-case result: 7 records, 5 planned, 2 blocked, 7 / 7 expected plan-status matches, 7 / 7 required action matches, 7 / 7 required issue matches, and 7 / 7 valid plan contracts.
- Week 4 completion audit result: advancement allowed is `true`; decision is `week4_complete_for_advancement_to_week5_scheduling`; blockers: none. The stricter audit checks that the scan plan includes `takeoff`, `fly_to`, `capture_images`, `run_vision_model`, `save_observation_results`, and `return_to_launch_area`, and that a Mermaid flow diagram exists.
- Required caveat: this is high-level mission planning over grounded synthetic-map commands. It is not scheduling, actual computer-vision inference, execution, route feasibility, or safety validation.

## Week 5 Multi-Drone Scheduling

The Week 5 slice allocates Week 4 planned tasks across a simulated three-drone fleet and compares deterministic assignment strategies. It uses classical scheduling baselines, not LLM assignment, and keeps scheduling separate from route optimization, safety validation, mission execution, and physical-drone control.

Run the default scheduling simulation:

```powershell
python scripts/schedule_missions.py
```

Audit Week 5 completion gates:

```powershell
python scripts/audit_week5_completion.py
```

Current Week 5 outputs:

- Strategy comparison JSON: `outputs/evaluations/week5_schedule_comparison_v1.json`
- Assignment report: `reports/week5_schedule_comparison_v1.md`
- Assignment CSV table: `outputs/tables/week5_assignments_least_loaded.csv`
- Allocation visualization: `outputs/visualizations/week5_drone_allocation_least_loaded.html`
- Completion gate audit: `outputs/evaluations/week5_completion_gate_audit.json` and `reports/week5_completion_gate_audit.md`
- Scheduler notebook: `notebooks/Notebook5_Scheduler.ipynb`

Current default example status: six schedulable tasks are assigned across three simulated drones, with no unassigned tasks. The compared strategies are `round_robin`, `least_loaded`, and `nearest_available`. The current synthetic example selects `least_loaded` as best by makespan, tied with `nearest_available`; this is not a general task-allocation claim.

## Week 6 Computer Vision Foundation

The Week 6 foundation selects Agriculture-Vision CVPR 2020 for the first non-commercial research experiment, validates provenance-aware aerial-image manifests, and provides a YOLO inference runner. Raw images are not committed because the dataset terms prohibit redistribution. Generic YOLO inference is only a smoke test because Agriculture-Vision is a semantic-segmentation benchmark.

The trainable Week 6 development baseline is a compact U-Net with ten output channels, masked multilabel BCE loss, official train/validation separation, seeded training, resumable checkpoints, and overlap-aware modified-mIoU evaluation. The initial T4 run used 64 train and 64 validation tiles for three epochs while loading zero test masks. It reached validation modified mIoU `0.0965`, dominated by background IoU `0.8022`; most anomaly classes remained at zero. This is a development and class-imbalance result, not final benchmark performance. See `docs/week6_segmentation_protocol.md` and `docs/week6_colab_run_log.md`.

The current leading development objective is BCE-Dice. On the fixed seed-17 256/256 T4 split it reached modified mIoU `0.15387`. A train-label-stratified 256/256 CPU diagnostic reached `0.15617`, but the required matched T4 run reached only `0.14852`; drydown remained the sole anomaly class with nonzero IoU. Stratified sampling is therefore not adopted under this configuration, the fixed-split T4 result remains the leading aggregate development result, and neither result is a final Agriculture-Vision benchmark.

Agriculture-Vision is one of five datasets recommended by the roadmap, not the only Week 6 dataset. Because it is a semantic-segmentation benchmark, it cannot by itself provide a labeled YOLO detection evaluation. The registered VisDrone2019-DET YOLOv8n baseline is now complete: 50 epochs on the official 6,471-image training split, evaluated on the official 548-image validation split without using test-dev for model selection. Post-training validation of `best.pt` produced precision `0.43116`, recall `0.32034`, mAP50 `0.29677`, and mAP50-95 `0.16724`. See `docs/week6_visdrone_detection_protocol.md`, `docs/week6_colab_run_log.md`, and `outputs/evaluations/week6_visdrone_yolov8n_seed17_e50_completed_summary.json`.

The roadmap-level Week 6 computer-vision milestone is complete for advancement. This means the project has reproducible image ingestion, inference, training, validation, provenance, checkpointing, and metric reporting. It does not mean that Agriculture-Vision segmentation is solved, that VisDrone performance is state of the art, or that vision has been integrated into end-to-end mission execution. See `docs/week6_completion_assessment.md`.

`notebooks/Notebook6_Vision.ipynb` uses a private Google Drive cache at `MyDrive/shepherd-ai-private/week6/` for the licensed archive, extracted pixels, and future checkpoints. The notebook links that cache into the repository layout during each Colab session, recalculates the archive SHA-256, and writes non-image provenance metadata under `outputs/evaluations/`. GitHub remains the source of truth for code, configurations, manifests, checksums, logs, and metrics; licensed pixels and large model state remain private and are not redistributed.

After reviewing and accepting the official Agriculture-Vision terms, prepare an extracted local subset:

```powershell
python scripts/prepare_agriculture_vision_subset.py --dataset-dir datasets/aerial_images/agriculture-vision --dataset-root . --split-json datasets/aerial_images/agriculture-vision/data2017_splits.json --output datasets/aerial_images/manifest.jsonl --max-per-split 10 --accept-terms
```

Validate a manifest after adding real image records:

```powershell
python scripts/validate_vision_manifest.py --manifest datasets/aerial_images/manifest.jsonl --dataset-root . --summary-output outputs/evaluations/week6_vision_manifest_summary.json
```

Install optional vision dependencies and run YOLO:

```powershell
python -m pip install -e .[vision]
python scripts/run_yolo_detection.py --manifest datasets/aerial_images/manifest.jsonl --dataset-root . --model yolov8n.pt --predictions-output outputs/evaluations/week6_yolo_detections.jsonl --summary-output outputs/evaluations/week6_yolo_detection_summary.json --annotated-dir outputs/visualizations/week6_yolo
```

Required caveat: detection counts are not detection performance. Do not report mAP, precision, recall, or mission success until labeled data, split definitions, and an evaluation protocol exist.

## Week 7 Safety, Feedback, and Integration

The Week 7 slice integrates typed intent extraction, explicit-map
grounding and clarification, mission planning, multi-drone scheduling, and a
deterministic pre-execution safety gate. Every assignment receives battery,
restricted-area, altitude, and current-availability checks. Missing evidence
blocks execution instead of passing silently. Thresholds are stored in the
synthetic development policy rather than hidden in source code.

Run one workflow and store the complete result:

```powershell
python scripts/run_week7_workflow.py --command "Send two drones north and scan the crops." --output outputs/evaluations/week7_safe_example.json
```

Run the registered 12-case preflight development evaluation:

```powershell
python scripts/evaluate_week7_safety.py
```

Run the registered eight-case event-driven supervision evaluation:

```powershell
python scripts/evaluate_week7_supervision.py
```

Run the remaining Week 7 evaluations and corrected completion audit:

```powershell
python scripts/evaluate_week7_clarification.py
python scripts/evaluate_week7_route_safety.py
python scripts/evaluate_week7_integration.py
python scripts/evaluate_week7_policy_sensitivity.py
python scripts/audit_week7_completion.py
```

The corrected evidence contains 12 preflight cases, 4 dialogue cases, 3
route-geometry cases, 8 event-driven supervision cases, 3 prior-module
integration cases, and 4 sensitivity dimensions. All registered expectations
and monotonicity checks match, and the corrected audit permits Week 8
advancement with no blockers. Unlike the earlier incorrect audit, documented
deferrals do not count as completed capabilities.

Supervisor events are driven by explicit synthetic telemetry snapshots, not
physical flight telemetry. Straight-line route checks and pairwise distance
monitoring are deterministic baselines; trajectory optimization, active
collision-avoidance control, weather, communications, dynamics,
mission-specific imagery, and Week 8 mission success remain unevaluated. See
`docs/week7_safety_protocol.md` and
`docs/week7_gap_audit.md`.

## Week 8 End-to-End Demonstration

Week 8 is in progress and follows `docs/week8_protocol.md`. The first slice
adds bounded compound-command decomposition and a shared multi-intent
preparation pipeline. It does not silently collapse the roadmap's two clauses
into one three-drone intent.

Run and store the exact typed roadmap preflight:

```powershell
python scripts/run_week8_preflight.py --output outputs/evaluations/week8_roadmap_scenario_typed_preflight.json
```

Without a recorded operator resolution, the expected result is
`clarification_required`. The first clause
grounds `north` and `crops` to North Field. The second grounds `east` to East
Field and `irrigation` to Irrigation Canal, which are distinct records in the
custom map. The pipeline preserves that contradiction as a negative result and
does not schedule the mission until the intended map relation is resolved. The
operator has now selected East Field for clause 2, and that choice is stored as
an explicit resolution while irrigation remains the semantic inspection target.

Run the resolved three-drone movement simulation:

```powershell
python scripts/run_week8_simulation.py --output outputs/evaluations/week8_roadmap_scenario_simulation.json --telemetry-output outputs/evaluations/week8_roadmap_scenario_telemetry.jsonl --map-output outputs/visualizations/week8_roadmap_scenario_simulation.html
```

The output includes a deterministic 2D round-trip simulation, time-stamped raw
telemetry, runtime inter-drone separation checks, phase-change events, and an
animated Folium map. Static formation slots keep the two North Field drones at
separate inspection points. This is not aerodynamic simulation, active
collision avoidance, ASR evidence, or mission-specific vision evidence.

Audit all Week 8 completion requirements against stored artifacts:

```powershell
python scripts/audit_week8_completion.py
```

The frozen expanded85 DistilBERT checkpoint has now been run locally on the two
fixed clauses. It produced one exact structured-intent match out of two and
9/10 matching fields; clause 2 incorrectly selected `send` rather than
`inspect`. This is scenario-development evidence and does not replace the held-
out Week 2 benchmark.

The complete Colab sequence is in `notebooks/Notebook8_FinalDemo.ipynb`. It:

1. registers and transcribes one exact human WAV;
2. runs the frozen trained intent checkpoint;
3. executes the resolved three-drone software simulation;
4. excludes Week 6 development IDs and evaluates the frozen Agriculture-Vision
   checkpoint on label-positive validation-remainder records;
5. builds all five roadmap metrics, the mission report, log, screenshot, and
   completion audit; and
6. saves a non-pixel, non-checkpoint artifact bundle to private Google Drive.

The current expected audit decision remains to stay on Week 8 until the Colab
audio and vision cells produce their raw evidence. Missing files are not
converted into zero-valued results.

The previously explored Three.js and Gazebo paths were discontinued on
2026-07-21 and are not part of the active architecture. Their stored reports
remain negative experiment history; they are not Week 8 completion evidence.

Week 8 remains blocked on a human-recorded WAV of the exact scenario and the
private-Drive Agriculture-Vision holdout inference. Existing Week 6 development
summaries and abandoned simulator frames are not relabeled as mission
observations. The notebook now constructs the mission manifest, raw predictions,
metrics, and reports from source artifacts and refuses completion when any stage
is absent.

## First Milestone

The first implemented milestone is a typed-command intent extraction baseline from Week 2 of the roadmap. It accepts simple typed mission commands and emits JSON fields aligned with the roadmap: `action`, `count`, `location`, `target`, and `constraints`.

Audio model evaluation is separate from text intent extraction. The repository has 10 self-recorded WAV command records under `datasets/sample_audio/`. A local-GPU Whisper ASR result has been recorded, but a Colab/T4 ASR result has not, because the WAV files are intentionally not tracked in the public GitHub repository.

Current corrective status: Week 2 is not research-complete. The repository now has a Week 2 completion gate that blocks advancement until a clean post-development benchmark exists.

Run the Week 2 completion audit:

```powershell
python scripts/audit_week2_completion.py
```

Create the blank post-development audio packet:

```powershell
python scripts/create_week2_audio_generalization_packet.py --commands datasets/commands/human_written_commands_curated_v1.jsonl --spans datasets/commands/human_verified_span_commands.jsonl --existing-audio-manifest datasets/sample_audio/manifest.jsonl --existing-audio-manifest datasets/sample_audio/audio_generalization_manifest.jsonl --existing-audio-manifest datasets/sample_audio/audio_v2_holdout_manifest.jsonl --dataset-root . --jsonl-output reports/week2_post_development_audio_packet.jsonl --markdown-output reports/week2_post_development_audio_packet.md --record-prefix audio_postdev --source manual_week2_post_development_audio_v1 --validation-count 10 --test-count 20
```

After filling the packet and placing WAV files at the packet paths, build the manifest:

```powershell
python scripts/build_audio_manifest_from_packet.py --packet reports/week2_post_development_audio_packet.jsonl --dataset-root . --manifest-output datasets/sample_audio/audio_post_development_manifest.jsonl --summary-output outputs/evaluations/audio_post_development_manifest_summary.json
```

Current Week 2 completion blockers:

- Fresh post-development manifest non-overlap audit is missing.
- Fresh audio-intent labels are not yet human-reviewed.
- Fresh ASR evaluation is missing.
- Fresh intent evaluation across competing systems is missing.

## Speech Input Scaffold

Milestone 2 currently validates audio/transcript manifests, evaluates transcript text, and includes a GPU-oriented Whisper transcription script. A first raw Whisper ASR evaluation has been run on the local `NVIDIA GeForce GTX 1650 SUPER` GPU, not on Colab/T4.

Manifest records should point to WAV files under the dataset root and include transcript provenance fields. See `docs/milestone_2_speech_input.md`.

Run Whisper ASR in Colab or another documented GPU environment:

```powershell
python scripts/transcribe_audio_whisper.py --manifest datasets/sample_audio/manifest.jsonl --dataset-root . --predictions-output outputs/evaluations/whisper_base_audio_predictions.jsonl --evaluation-output outputs/evaluations/whisper_base_audio_evaluation.json --model base --device cuda --language en --required-device-substring T4
```

The script writes raw predicted transcripts separately from the WER/exact-match evaluation.

Recorded local-GPU Whisper `base` ASR run, July 4, 2026:

- Predictions: `outputs/evaluations/whisper_base_audio_predictions_local_gtx1650.jsonl`
- Evaluation: `outputs/evaluations/whisper_base_audio_evaluation_local_gtx1650.json`
- Error analysis: `outputs/evaluations/whisper_base_audio_error_analysis_local_gtx1650.json`
- Split summary: `outputs/evaluations/whisper_base_audio_split_summary_local_gtx1650.json`
- Intent impact: `outputs/evaluations/whisper_base_intent_impact_local_gtx1650.json`
- Intent accuracy: `outputs/evaluations/whisper_base_intent_accuracy_local_gtx1650.json`
- Span impact: `outputs/evaluations/whisper_base_span_impact_local_gtx1650.json`
- Device: `NVIDIA GeForce GTX 1650 SUPER`
- Flags: `--device cuda --language en --required-device-substring GTX --no-fp16`
- Exact-match accuracy: `0.9`
- Mean word error rate: `0.01`
- Observed normalized word substitution: `fifty -> 50`

The audio manifest now has a retrospective seed-17 split: 6 train, 2 validation, and 2 test records. The split-level summary shows validation and test WER `0.0` on two records each, while the single `fifty -> 50` substitution is in train. This is still not a final audio benchmark because the split was assigned after the first pooled ASR result existed.

The ASR-to-intent impact analysis compares intent outputs from human transcripts and Whisper transcripts. It is not intent accuracy because no gold audio-intent labels are used for the original 10-record sample. Historical result: the `fifty -> 50` ASR substitution changed the raw extracted `constraints` string for one record under both `deterministic_v1` and `trained_nb_human_curated_v2`, but the normalized semantic intent comparison and canonical altitude-constraint comparison treated the two constraints as equivalent.

The audio-linked intent accuracy analysis reuses matching labels from `datasets/commands/human_written_commands_curated_v1.jsonl`; it does not create new gold labels. Current result on the 10 audio transcripts: human transcripts score exact-record accuracy `1.0`, and Whisper transcripts score `0.9` because the raw constraint string differs for `fifty` versus `50`.

The ASR-to-span impact analysis reuses matching labels from `datasets/commands/human_verified_span_commands.jsonl` for human-transcript accuracy, then compares span tagger predictions on human transcripts versus Whisper transcripts. Current result on the 10 matched audio transcripts: human-transcript span entity F1 is `0.7324` with `span_nb_v1`; Whisper changes one raw predicted constraint entity because `fifty` becomes `50`, but number-normalized semantic span predictions are unchanged. This is not ASR span accuracy because no separate human gold spans exist for the Whisper transcript text.

The current parser, transcript utilities, and constraint normalizer are not trained models. The constraint normalizer currently canonicalizes simple altitude-limit phrases such as `below fifty meters` and `below 50 meters`; it is not safety validation. A serious Week 2 implementation needs labeled command data, split definitions, and a trained or fine-tuned intent extraction component, with deterministic baselines retained for comparison.

## Week 2 Intent Training

The first supervised intent-extraction baseline is documented in `docs/week2_intent_training.md`.

Run the preserved weak baseline:

```powershell
python scripts/train_intent_model.py --dataset datasets/commands/intent_labeled_synthetic.jsonl --model-output outputs/model_artifacts/intent_nb_v0.json --metrics-output outputs/evaluations/intent_nb_v0_metrics.json --comparison-output outputs/evaluations/intent_nb_v0_vs_deterministic.json --validation-output outputs/evaluations/intent_nb_v0_validation_metrics.json --seed 17
```

Run the improved Week 2 baseline:

```powershell
python scripts/train_intent_model.py --dataset datasets/commands/intent_labeled_synthetic.jsonl --model-output outputs/model_artifacts/intent_nb_v1.json --metrics-output outputs/evaluations/intent_nb_v1_metrics.json --comparison-output outputs/evaluations/intent_nb_v1_vs_deterministic.json --validation-output outputs/evaluations/intent_nb_v1_validation_metrics.json --seed 17 --model-name trained_nb_v1 --model-version 0.2 --include-bigrams --include-alias-features --alias-feature-weight 3
```

Current synthetic held-out result:

- `trained_nb_v0`: test field accuracy 0.85, exact-record accuracy 0.25; validation field accuracy 0.95, exact-record accuracy 0.75.
- `trained_nb_v1`: test field accuracy 1.0, exact-record accuracy 1.0; validation field accuracy 1.0, exact-record accuracy 1.0.
- `deterministic_v0`: field accuracy 1.0, exact-record accuracy 1.0 on the same tiny synthetic test split.

The `trained_nb_v1` result comes from a tiny synthetic test split and field-specific schema-alias features. It is a reproducible Week 2 training workflow check, not a real-user or speech-recognition result.

Current deterministic parser status: new parser outputs are labeled `deterministic_v2`. `deterministic_v1` added an open-vocabulary target phrase fallback for supported Week 2 actions. `deterministic_v2` adds post-hoc fixes for the reviewed audio-generalization batch, including `scan/search/check X for Y` location-target separation, map/monitor/photograph normalization, broader open-vocabulary locations, compound-command constraints, and a few ASR-confusion patterns such as `survey -> server`. It is still a deterministic baseline, not a trained model.

Current curated user-command result:

- Dataset: `datasets/commands/human_written_commands_curated_v1.jsonl`
- Split: 30 train, 10 validation, 10 test.
- `trained_nb_human_curated_v1`: validation field accuracy 0.78, test field accuracy 0.70.
- `trained_nb_human_curated_v2`: validation field accuracy 1.0, test field accuracy 1.0.
- `deterministic_v0`: test field accuracy 1.0, exact-record accuracy 1.0.

`trained_nb_human_curated_v1` is the preserved negative result for the trained field classifier. `trained_nb_human_curated_v2` is a hybrid parser-gated baseline with deterministic rule overrides, not proof that a pure trained model solved the task.

The deterministic metrics above are historical outputs generated before the current `deterministic_v2` parser label. Rerun the evaluation scripts to generate fresh raw artifacts for the current parser.

Evaluate a saved model on a selected split without retraining:

```powershell
python scripts/evaluate_intent_model.py --model outputs/model_artifacts/intent_nb_v1.json --dataset datasets/commands/intent_labeled_synthetic.jsonl --split validation --output outputs/evaluations/intent_nb_v1_saved_model_validation.json
```

Week 2 data collection rules are documented in `docs/week2_data_collection_protocol.md`. The current training method and suggested paper reading order are documented in `docs/week2_training_explainer.md`.

Span annotation for stronger slot extraction is documented in `docs/week2_span_annotation.md`. The repository now includes a dependency-free validator and BIO exporter for future spaCy or Hugging Face token-classification work:

```powershell
python scripts/create_span_record.py --output datasets/commands/human_verified_span_commands.jsonl --id span_cmd_001 --text "Send the nearest drone to inspect the livestock pen without crossing the road." --split train --target-span "livestock pen" --constraint-span "without crossing the road" --action-span "inspect"
python scripts/create_span_record_from_command.py --input datasets/commands/human_written_commands_curated_v1.jsonl --id human_cmd_001 --output datasets/commands/human_verified_span_commands.jsonl --count-span "two drones" --location-span "north" --action-span "inspect" --target-span "crops"
python scripts/rebuild_span_dataset_from_commands.py --commands-file span_label_commands.txt --output datasets/commands/human_verified_span_commands.jsonl --summary-output outputs/evaluations/human_verified_span_commands_summary.json --bio-output outputs/evaluations/human_verified_span_commands_bio.jsonl
python scripts/validate_span_dataset.py --dataset datasets/commands/human_verified_span_commands.jsonl --summary-output outputs/evaluations/human_verified_span_commands_summary.json --bio-output outputs/evaluations/human_verified_span_commands_bio.jsonl
```

This command requires a real span-labeled dataset. Do not treat parser drafts or assistant-curated record labels as human-verified span labels.

Train the initial supervised BIO span tagger:

```powershell
python scripts/train_span_tagger.py --dataset datasets/commands/human_verified_span_commands.jsonl --model-output outputs/model_artifacts/span_nb_v0.json --metrics-output outputs/evaluations/span_nb_v0_metrics.json --validation-output outputs/evaluations/span_nb_v0_validation_metrics.json --seed 17 --model-name span_nb_v0 --model-version 0.1
python scripts/train_span_tagger.py --dataset datasets/commands/human_verified_span_commands.jsonl --model-output outputs/model_artifacts/span_nb_v1.json --metrics-output outputs/evaluations/span_nb_v1_metrics.json --validation-output outputs/evaluations/span_nb_v1_validation_metrics.json --seed 17 --model-name span_nb_v1 --model-version 0.2 --use-transitions
```

Current span-tagger results on human-verified span labels:

- `span_nb_v0`: validation token accuracy 0.6857, validation entity F1 0.4969; test token accuracy 0.6667, test entity F1 0.4646.
- `span_nb_v1`: validation token accuracy 0.7143, validation entity F1 0.5753; test token accuracy 0.7018, test entity F1 0.5870.

These are honest early baselines, not solved slot extractors.

Export a Colab-ready Hugging Face token-classification dataset:

```powershell
python scripts/export_hf_token_dataset.py --dataset datasets/commands/human_verified_span_commands.jsonl --output-dir outputs/hf_token_dataset
```

Fine-tune the transformer baseline in Google Colab with a T4 GPU runtime. In Colab, select `Runtime > Change runtime type > T4 GPU`, then verify CUDA before training:

```python
import torch

assert torch.cuda.is_available(), "Select a Colab GPU runtime before training"
print(torch.cuda.get_device_name(0))
```

Then run:

```powershell
python scripts/train_hf_token_classifier.py --dataset-dir outputs/hf_token_dataset --pretrained-model distilbert-base-uncased --output-dir outputs/model_artifacts/hf_token_classifier_distilbert_colab_t4 --metrics-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_metrics.json --validation-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_validation_metrics.json --epochs 30 --learning-rate 0.00005 --batch-size 8 --seed 17 --required-device-substring T4
```

The script refuses to train without CUDA. Do not report a Hugging Face fine-tuning result as provenance-complete unless the raw metrics file records the runtime, model, seed, parameters, split, and package versions.

Completed Colab/T4 DistilBERT token-classifier run, July 2, 2026:

- Notebook: `notebooks/Notebook2_NLP_Colab_T4.ipynb`
- Runtime verified in Colab: `T4 (Python 3)`
- Runtime metadata recorded in `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_metrics.json`: CUDA enabled on `Tesla T4`; `torch` 2.11.0+cu128; `transformers` 5.12.1; `accelerate` 1.14.0; `datasets` 4.0.0.
- Validation entity F1: 0.7945
- Test entity F1: 0.5926
- Raw metrics copied back from Colab: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_metrics.json` and `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_validation_metrics.json`
- Record-level held-out predictions: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_predictions.json`
- Held-out BIO error analysis: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_error_analysis.json`
- Error profile: 9 of 10 test records contain at least one entity error; largest false-negative bucket is `target` with 4 missed entities, and largest false-positive buckets are `constraint` with 8 entities and `target` with 7 entities.

Reviewed-label Colab/T4 DistilBERT token-classifier retrain, July 4, 2026:

- Runtime verified in Colab: `T4 (Python 3)`
- Runtime metadata recorded in `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_metrics.json`: CUDA enabled on `Tesla T4`; `torch` 2.11.0+cu128; `transformers` 5.12.1; `accelerate` 1.14.0; `datasets` 4.0.0.
- Data: `outputs/hf_token_dataset`, regenerated after applying the reviewed span command subset.
- Validation entity F1: 0.7945
- Test entity F1: 0.6047
- Test token accuracy: 0.7281
- Raw metrics copied back from Colab: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_metrics.json` and `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_validation_metrics.json`
- Record-level held-out predictions: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_test_predictions.json`
- Held-out BIO error analysis: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_test_error_analysis.json`

This retrain improves the previous held-out test entity F1 from 0.5926 to 0.6047 on the same 10-record test split. It is still a small-data Week 2 baseline with substantial entity errors, not a solved intent extractor.

Plan the next targeted human span-data batch from the reviewed error analysis:

```powershell
python scripts/plan_week2_span_collection.py --span-dataset datasets/commands/human_verified_span_commands.jsonl --evaluation outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_test_predictions.json --error-analysis outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_test_error_analysis.json --json-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_collection_plan.json --markdown-output reports/week2_targeted_span_collection_plan.md
```

Current targeted collection plan: 35 new human-written, human-verified span records, focused on `target`, `constraint`, `count`, `action`, and `location` errors. The generated plan does not contain new command text or gold labels. Since it is derived from held-out test errors, use the targeted records for train/validation expansion and create a fresh held-out test set before making stronger model claims.

Create the blank collection packet:

```powershell
python scripts/create_week2_collection_packet.py --plan outputs/evaluations/hf_token_classifier_distilbert_colab_t4_reviewed_collection_plan.json --jsonl-output reports/week2_targeted_span_collection_packet.jsonl --markdown-output reports/week2_targeted_span_collection_packet.md
```

The current packet has 35 blank slots: 27 train and 8 validation. It is a worksheet only; it does not contain collected command text or labels.

Applied follow-up span batch, July 4, 2026:

- Corrected command file: `reports/week2_followup_span_commands_corrected.txt`
- Added 35 `manual_week2_span_annotation_v2` records to `datasets/commands/human_verified_span_commands.jsonl`
- Current span dataset: 85 records, split as 57 train, 18 validation, 10 test
- Current Hugging Face token dataset: 85 records and 809 tokens

Completed expanded 85-record Colab/T4 DistilBERT retrain, July 4, 2026:

- Runtime verified in Colab: `T4 (Python 3)`
- Data: 85-record `outputs/hf_token_dataset`
- Validation entity F1: 0.8382
- Test entity F1: 0.7857
- Test entity precision: 0.7500
- Test entity recall: 0.8250
- Test token accuracy: 0.8246
- Record-level held-out errors: 6 of 10 records still have at least one token error
- Raw artifacts: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_*`
- Review files: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_span_review_*`

This is the strongest Week 2 text-command span result so far, but it is not an ASR result and not end-to-end mission performance.

Evaluate whether token-classifier spans assemble into the roadmap intent JSON fields:

```powershell
python scripts/evaluate_span_intent_assembly.py --evaluation outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_test_predictions.json --output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_span_intent_assembly.json
```

Current span-to-intent assembly result:

- Report: `reports/week2_span_intent_assembly_report.md`
- Output: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_span_intent_assembly.json`
- Exact assembled-intent accuracy: 5 / 10 = 0.5000
- Field accuracy: 43 / 50 = 0.8600
- Field errors: `constraints`: 4, `location`: 2, `target`: 1
- Predicted intents with deterministic validation warnings: 4 / 10
- Validation warnings: `missing_expected_location`: 3, `suspicious_short_constraint`: 1
- Path comparison output: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_intent_path_comparison.json`
- On the same span-derived benchmark, `deterministic_v3` scores 1 / 10 exact and 0.5800 field accuracy, `span_intent_assembly` scores 5 / 10 exact and 0.8600 field accuracy, and post-hoc `hybrid_span_parser` scores 10 / 10 exact and 1.0000 field accuracy.
- This is a span-schema comparison, not audio-intent accuracy. The hybrid result was developed after inspecting the same 10 span-test errors, so treat it as Week 2 development evidence, not a clean generalization benchmark. It shows that the trained token classifier is useful, but that trained spans still need deterministic assembly and validation before later grounding or planning modules consume them.

Measure whether ASR transcript differences change span-assembled intent JSON:

```powershell
python scripts/analyze_asr_span_intent_impact.py --span-impact outputs/evaluations/whisper_base_span_impact_local_gtx1650.json --output outputs/evaluations/whisper_base_span_intent_impact_local_gtx1650.json
```

Current ASR span-to-intent impact result on the 10-record local audio sample:

- Output: `outputs/evaluations/whisper_base_span_intent_impact_local_gtx1650.json`
- `span_intent_assembly`: 1 / 10 intent changes from human transcript to Whisper transcript
- `hybrid_span_parser`: 1 / 10 intent changes from human transcript to Whisper transcript
- The changed record is a raw constraint-string difference: `below fifty meters` versus `below 50 meters`. This is impact analysis, not gold ASR intent accuracy.

Run the saved Colab/T4 transformer checkpoint directly on transcript records:

```powershell
python scripts/predict_hf_token_classifier_transcripts.py --input-jsonl outputs/evaluations/whisper_base_audio_predictions_local_gtx1650.jsonl --model-dir outputs/model_artifacts/hf_token_classifier_distilbert_colab_t4_expanded85 --transcript-field expected_transcript --output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_human_transcript_predictions.json --required-device-substring T4
python scripts/predict_hf_token_classifier_transcripts.py --input-jsonl outputs/evaluations/whisper_base_audio_predictions_local_gtx1650.jsonl --model-dir outputs/model_artifacts/hf_token_classifier_distilbert_colab_t4_expanded85 --transcript-field predicted_transcript --output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_asr_transcript_predictions.json --required-device-substring T4
```

The checkpoint directory is intentionally ignored by git because it contains generated model weights. These commands must be run in the same Colab/T4 environment after training or after restoring the checkpoint directory into `outputs/model_artifacts/`.

Imported checkpoint and transcript-intent evaluation, July 6, 2026:

- Downloaded checkpoint zip: `D:\Users\momoa\Downloads\hf_token_classifier_distilbert_colab_t4_expanded85.zip`
- Imported checkpoint directory: `outputs/model_artifacts/hf_token_classifier_distilbert_colab_t4_expanded85`
- Report: `reports/week2_transformer_transcript_intent_report.md`
- Human/reference transcript intent evaluation on `audio_v2_holdout`: `deterministic_v3` exact accuracy 30 / 30 = 1.0000, `hybrid_span_parser` 6 / 30 = 0.2000, `span_intent_assembly` 5 / 30 = 0.1667.
- ASR/Whisper transcript intent evaluation on `audio_v2_holdout`: `deterministic_v3` exact accuracy 27 / 30 = 0.9000, `hybrid_span_parser` 5 / 30 = 0.1667, `span_intent_assembly` 4 / 30 = 0.1333.
- Interpretation: the imported transformer span model is not currently competitive with the deterministic parser for final intent JSON on this audio-linked benchmark. This is a useful negative result and a target for improving span-to-intent assembly, not evidence that training was useless.
- Error analysis: `reports/week2_transformer_transcript_intent_error_analysis.md`
- Human span-remediation worksheet: `reports/week2_audio_v2_span_remediation_packet.md`; this has blank spans and is not gold data until reviewed.

Week 2 to Week 3 NLP handoff:

- Handoff report: `reports/week2_to_week3_nlp_handoff.md`
- Machine-readable handoff: `outputs/evaluations/week2_to_week3_nlp_handoff.json`
- Provisional Week 3 input path: `deterministic_v3` intent JSON.
- Required caveat: this is a development handoff, not a claim that Week 2 NLP is solved or that `deterministic_v3` has clean final benchmark evidence.

Package the trained checkpoint for download from Colab:

```powershell
python scripts/package_hf_checkpoint.py --model-dir outputs/model_artifacts/hf_token_classifier_distilbert_colab_t4_expanded85 --output-zip /content/hf_token_classifier_distilbert_colab_t4_expanded85.zip --include outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_metrics.json --include outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_validation_metrics.json --include outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_test_predictions.json --include outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_test_error_analysis.json
```

Then download `/content/hf_token_classifier_distilbert_colab_t4_expanded85.zip` from the Colab Files pane. The zip should contain `hf_token_classifier_distilbert_colab_t4_expanded85/model.safetensors`, `config.json`, tokenizer files, and `checkpoint_manifest.json`.

Import the downloaded checkpoint zip locally:

```powershell
python scripts/import_hf_checkpoint.py --checkpoint-zip D:\Users\momoa\Downloads\hf_token_classifier_distilbert_colab_t4_expanded85.zip --output-dir outputs/model_artifacts --expected-name hf_token_classifier_distilbert_colab_t4_expanded85 --overwrite
```

Do not pass the downloaded `.ipynb` or `.py` notebook export to this command; those files confirm the run and metrics but do not contain model weights.

Current Week 2 status summary:

```powershell
python scripts/summarize_week2_status.py --audio-evaluation outputs/evaluations/whisper_base_audio_evaluation_local_gtx1650.json --intent-accuracy outputs/evaluations/whisper_base_intent_accuracy_local_gtx1650.json --intent-impact outputs/evaluations/whisper_base_intent_impact_local_gtx1650.json --span-impact outputs/evaluations/whisper_base_span_impact_local_gtx1650.json --hf-token-metrics outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_metrics.json --hf-token-error-analysis outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_test_error_analysis.json --span-intent-comparison outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_intent_path_comparison.json --asr-span-intent-impact outputs/evaluations/whisper_base_span_intent_impact_local_gtx1650.json --hf-transcript-human-intent-accuracy outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_audio_v2_holdout_human_transcript_intent_accuracy.json --hf-transcript-asr-intent-accuracy outputs/evaluations/hf_token_classifier_distilbert_colab_t4_expanded85_audio_v2_holdout_asr_transcript_intent_accuracy.json --output-json outputs/evaluations/week2_status_summary.json --output-markdown reports/week2_status_summary.md
```

The generated report is `reports/week2_status_summary.md`, with machine-readable output in `outputs/evaluations/week2_status_summary.json`.

Performance-risk audit for interpreting the current high metrics:

```powershell
python scripts/audit_week2_performance_risks.py --commands datasets/commands/human_written_commands_curated_v1.jsonl --spans datasets/commands/human_verified_span_commands.jsonl --audio-manifest datasets/sample_audio/manifest.jsonl --dataset-root . --status-summary outputs/evaluations/week2_status_summary.json --intent-model outputs/model_artifacts/intent_nb_human_curated_v2.json --output-json outputs/evaluations/week2_performance_risk_audit.json --output-markdown reports/week2_performance_risk_audit.md
```

The audit is `reports/week2_performance_risk_audit.md`, with machine-readable output in `outputs/evaluations/week2_performance_risk_audit.json`.

Pre-register a fresh non-overlapping audio batch before the next ASR run:

```powershell
python scripts/create_week2_audio_generalization_packet.py --commands datasets/commands/human_written_commands_curated_v1.jsonl --spans datasets/commands/human_verified_span_commands.jsonl --existing-audio-manifest datasets/sample_audio/manifest.jsonl --existing-audio-manifest datasets/sample_audio/audio_generalization_manifest.jsonl --dataset-root . --jsonl-output reports/week2_audio_v2_holdout_packet.jsonl --markdown-output reports/week2_audio_v2_holdout_packet.md --validation-count 10 --test-count 20 --record-prefix audio_v2_holdout --source manual_week2_audio_v2_holdout_v1
```

After real WAVs and human-verified transcripts are collected into a candidate manifest, audit it for overlap before ASR:

```powershell
python scripts/audit_week2_audio_generalization_manifest.py --candidate-manifest datasets/sample_audio/audio_v2_holdout_manifest.jsonl --commands datasets/commands/human_written_commands_curated_v1.jsonl --spans datasets/commands/human_verified_span_commands.jsonl --existing-audio-manifest datasets/sample_audio/manifest.jsonl --existing-audio-manifest datasets/sample_audio/audio_generalization_manifest.jsonl --dataset-root . --output outputs/evaluations/week2_audio_v2_holdout_manifest_audit.json --fail-on-overlap
```

The v2 holdout packet is `reports/week2_audio_v2_holdout_packet.md` and `reports/week2_audio_v2_holdout_packet.jsonl`. It was filled as `datasets/sample_audio/audio_v2_holdout_manifest.jsonl` with 30 non-overlapping recordings. Its purpose is to test whether `deterministic_v2` generalizes beyond the reviewed batch that motivated it.

Completed local-GPU Whisper run on the fresh v2 audio holdout:

- Manifest: `datasets/sample_audio/audio_v2_holdout_manifest.jsonl`
- Report: `reports/week2_audio_v2_holdout_asr_report.md`
- Exact transcript accuracy: 22 / 30 = 0.7333
- Mean word error rate: 0.0485
- Validation exact transcript accuracy: 6 / 10 = 0.6000
- Test exact transcript accuracy: 16 / 20 = 0.8000
- ASR-to-intent semantic changes with `deterministic_v2`: 5 / 30 records
- Human-reviewed intent labels: `datasets/commands/audio_v2_holdout_human_verified_intents.jsonl`
- Human-reviewed label summary: `outputs/evaluations/audio_v2_holdout_human_verified_intents_summary.json`
- Human-reviewed intent accuracy: `outputs/evaluations/whisper_base_audio_v2_holdout_intent_accuracy_human_verified_local_gtx1650.json`
- `deterministic_v2` exact intent accuracy: 16 / 30 = 0.5333 on human transcripts; 14 / 30 = 0.4667 on Whisper transcripts
- `trained_nb_human_curated_v2` exact intent accuracy: 16 / 30 = 0.5333 on human transcripts; 14 / 30 = 0.4667 on Whisper transcripts
- Post-hoc `deterministic_v3` development accuracy: `outputs/evaluations/whisper_base_audio_v2_holdout_intent_accuracy_human_verified_v3_local_gtx1650.json`
- `deterministic_v3` exact intent accuracy on the same reviewed holdout: 30 / 30 = 1.0000 on human transcripts; 27 / 30 = 0.9000 on Whisper transcripts
- Caveat: the `deterministic_v3` result is same-holdout parser development after error inspection, not a clean generalization benchmark.

The v2 holdout intent labels were applied from the human-reviewed command file:

- Draft packet: `reports/week2_audio_v2_holdout_intent_review_packet.jsonl`
- Editable review file: `reports/week2_audio_v2_holdout_intent_review_commands.jsonl`
- Applied labels: `datasets/commands/audio_v2_holdout_human_verified_intents.jsonl`
- Current readiness: 30 reviewed records, 0 draft records, ready for gold evaluation.

Pre-registered follow-up packet for clean `deterministic_v3` validation:

- Packet: `reports/week2_audio_v3_holdout_packet.jsonl`
- Worksheet: `reports/week2_audio_v3_holdout_packet.md`
- Slots: 30 blank slots, 10 validation and 20 test
- Source for future records: `manual_week2_audio_v3_holdout_v1`
- Existing normalized texts blocked for overlap: 141
- Current status: no audio, transcripts, ASR output, intent labels, or evaluation result exists for this packet yet.

Completed local-GPU Whisper run on the non-overlapping 30-record audio generalization batch:

- Manifest: `datasets/sample_audio/audio_generalization_manifest.jsonl`
- Report: `reports/week2_audio_generalization_asr_report.md`
- Exact transcript accuracy: `0.60`
- Mean word error rate: `0.0716`
- Downstream semantic intent changes: 7 of 30 records
- Important caveat: this is local GTX, not Colab/T4, and it is ASR-to-intent impact rather than gold intent accuracy.

Human-reviewed audio-intent labels have now been applied for this same 30-record batch:

- Gold candidate: `datasets/commands/audio_generalization_human_verified_intents.jsonl`
- Review summary: `outputs/evaluations/audio_generalization_human_verified_intents_summary.json`
- Initial reviewed intent accuracy: `outputs/evaluations/whisper_base_audio_generalization_intent_accuracy_human_verified_local_gtx1650.json`
- Post-hoc `deterministic_v2` intent accuracy: `outputs/evaluations/whisper_base_audio_generalization_intent_accuracy_human_verified_v2_local_gtx1650.json`
- Readiness: 30 records, 0 draft records, 0 unreviewed records.
- Initial `deterministic_v1` on human transcripts: exact-record accuracy 7 / 30 = 0.2333; field accuracy 0.6667.
- Initial `deterministic_v1` on Whisper transcripts: exact-record accuracy 4 / 30 = 0.1333; field accuracy 0.6133.
- Post-hoc `deterministic_v2` on human transcripts: exact-record accuracy 27 / 30 = 0.9000; field accuracy 0.9600.
- Post-hoc `deterministic_v2` on Whisper transcripts: exact-record accuracy 19 / 30 = 0.6333; field accuracy 0.8933.
- `trained_nb_human_curated_v2` currently matches the deterministic result on this batch because it is a parser-gated hybrid baseline.

This is the strongest current evidence that Week 2 intent extraction improves with structured error analysis but is not solved. Because `deterministic_v2` was created after reviewing this batch, the same 30 records are not a clean final benchmark for it.

Create draft intent labels for human review before reporting gold intent accuracy on the new audio batch:

```powershell
python scripts/create_week2_audio_intent_review_packet.py --manifest datasets/sample_audio/audio_generalization_manifest.jsonl --dataset-root . --jsonl-output reports/week2_audio_generalization_intent_review_packet.jsonl --markdown-output reports/week2_audio_generalization_intent_review_packet.md
```

The source review packet is `reports/week2_audio_generalization_intent_review_packet.md`. It has 30 parser-draft labels and remains preserved as a draft artifact. The reviewed compact file and applied gold candidate are separate artifacts listed above.

Export the draft packet into a compact editable review file:

```powershell
python scripts/export_audio_intent_review_commands.py --packet reports/week2_audio_generalization_intent_review_packet.jsonl --commands-output reports/week2_audio_generalization_intent_review_commands.jsonl --report-output reports/week2_audio_generalization_intent_review_commands.md
```

Open `reports/week2_audio_generalization_intent_review_commands.md` beside `reports/week2_audio_generalization_intent_review_commands.jsonl`. For each JSONL line, correct only the intent fields after human review of the transcript: `action`, `count`, `location`, `target`, and `constraints`. When a line has been reviewed, set `review_status` to `human_reviewed`, `data_type` to `human_verified_audio_intent_command`, and `label_source` to `human_reviewed_v1`.

Apply the reviewed compact file back into a full gold-label candidate:

```powershell
python scripts/apply_audio_intent_review_commands.py --packet reports/week2_audio_generalization_intent_review_packet.jsonl --commands-file reports/week2_audio_generalization_intent_review_commands.jsonl --output datasets/commands/audio_generalization_human_verified_intents.jsonl --summary-output outputs/evaluations/audio_generalization_human_verified_intents_summary.json --require-reviewed
```

This command should fail until every record has actually been marked as human-reviewed.

Validate review readiness before using any audio-intent JSONL as gold labels:

```powershell
python scripts/validate_audio_intent_review_packet.py --packet reports/week2_audio_generalization_intent_review_packet.jsonl --summary-output outputs/evaluations/week2_audio_generalization_intent_review_packet_summary.json --require-reviewed
```

The current draft packet intentionally fails `--require-reviewed`. After applying a fully reviewed compact file, validate `datasets/commands/audio_generalization_human_verified_intents.jsonl` instead.

After training, run record-level transformer evaluation and BIO error analysis in the same Colab T4 runtime:

```powershell
python scripts/evaluate_hf_token_classifier.py --dataset-dir outputs/hf_token_dataset --model-dir outputs/model_artifacts/hf_token_classifier_distilbert_colab_t4 --split test --evaluation-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_predictions.json --error-analysis-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_error_analysis.json --required-device-substring T4
```

Build a prioritized human-review queue from held-out transformer errors:

```powershell
python scripts/build_span_review_queue.py --evaluation outputs/evaluations/hf_token_classifier_distilbert_colab_t4_test_predictions.json --output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_queue.jsonl --summary-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_summary.json --focus-field target --focus-field constraint
```

This queue is not corrected training data. It marks model predictions as `model_generated_not_gold` and points to records that need human review before labels are changed or reused for training.

Export the queued records into an editable command file and a review report:

```powershell
python scripts/export_span_review_commands.py --span-dataset datasets/commands/human_verified_span_commands.jsonl --review-queue outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_queue.jsonl --commands-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_commands.txt --report-output outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_report.md --source-command-dataset datasets/commands/human_written_commands_curated_v1.jsonl
```

Open the report and command file together. Edit the command file only after human review, then apply the reviewed subset back into the full span dataset:

```powershell
python scripts/apply_span_review_commands.py --base-dataset datasets/commands/human_verified_span_commands.jsonl --commands-file outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_commands.txt --output datasets/commands/human_verified_span_commands.jsonl --summary-output outputs/evaluations/human_verified_span_commands_summary.json --bio-output outputs/evaluations/human_verified_span_commands_bio.jsonl
```

Use `apply_span_review_commands.py` for review subsets so unreviewed records are preserved. `rebuild_span_dataset_from_commands.py` is for full command files that intentionally recreate the whole dataset.

Create and validate real Week 2 command data only when the records are actually collected:

```powershell
python scripts/collect_week2_sample.py --text "Send two drones north and inspect the crops." --wav "C:\path\to\your_recording.wav" --split train
python scripts/create_command_record.py --output datasets/commands/human_written_commands.jsonl --id human_cmd_001 --text "Send two drones north and inspect the crops." --split train --source human_written_collection_v1 --data-type human_written_command --action inspect --count 2 --location north --target crops
python scripts/validate_command_dataset.py --dataset datasets/commands/human_written_commands.jsonl --summary-output outputs/evaluations/human_written_commands_summary.json --require-splits train,validation,test
python scripts/validate_audio_manifest.py --manifest datasets/sample_audio/manifest.jsonl --dataset-root . --summary-output outputs/evaluations/audio_manifest_summary.json
python scripts/audit_week2_collection.py --commands datasets/commands/human_written_commands_draft.jsonl --audio-manifest datasets/sample_audio/manifest.jsonl --dataset-root . --output outputs/evaluations/week2_collection_audit.json
```

The first command is the easiest path: type the transcript and pass a WAV path. It writes draft intent labels from the deterministic parser, marked with the current parser version such as `deterministic_v2_draft`. Review those labels before using them as human-verified training or evaluation labels.

These commands are for real collection files. The repository currently includes command collection artifacts and an audio manifest, but those are not a final human-verified benchmark or a Whisper ASR evaluation.

## Historical Week 9 Evidence-Aware Evaluation

This section documents the superseded paper direction. Its code and outputs
remain useful development evidence, but they are not part of the active
MultiUAV-Plat paper's results.

The historical revision evaluates Shepherd-AI's explicit `proceed`,
`clarify`, and `block` decisions. The benchmark reuses the 22 human-written
Week 3 grounding commands and registered synthetic Week 7 cases, then adds four
explicitly synthetic conflict controls. It reports false refusals, silent
misexecution, clarification recall, block recall, and clarification recovery.

Run the stored evaluation:

```powershell
python scripts/evaluate_evidence_aware_decisions.py
```

The comparison system is a command-only no-evidence-gate ablation. It is not a
TACOS reimplementation and not a monolithic LLM result. See
`docs/week9_evidence_aware_protocol.md` and
`reports/week9_evidence_aware_decisions_v1.md` for definitions and claim
limits. The low Week 8 agricultural vision result remains part of the paper and
is not replaced by this decision diagnostic.

The next comparison is implemented but not yet run. Build its label-separated
packet locally:

```powershell
python scripts/build_monolithic_decision_packet.py
```

Run `scripts/run_hf_monolithic_decision_baseline.py` in a Colab T4 runtime,
then score the preserved raw responses with:

```powershell
python scripts/evaluate_monolithic_decision_baseline.py
```

The default baseline is `Qwen/Qwen2.5-7B-Instruct` loaded in 4-bit mode. The
runner resolves an exact model commit, records all package and decoding
parameters, refuses CPU execution, never loads the separate gold file, and can
resume interrupted Colab runs. See
`docs/week9_monolithic_baseline_protocol.md`.

A fresh human-held-out benchmark does not yet exist. The repository now has a
reproducible collection pipeline for frozen contexts, label-blinded review,
third-party disagreement adjudication, overlap/context validation, and
label-separated inference packets. It does not generate commands or pretend
that review occurred. Follow `docs/human_evidence_benchmark_protocol.md`; a
candidate must pass `scripts/validate_human_evidence_benchmark.py` before
inference.

The first Colab T4 diagnostic completed on 38 reused development cases with
`Qwen/Qwen2.5-7B-Instruct` at revision
`a09a35458c702b33eeacc393d103063234e8bc28`. Shepherd scored `1.0000`
decision accuracy and the monolithic baseline scored `0.6842`; this is not a
held-out result. The raw run and evaluator outputs are preserved in the
verified Google Drive archive registered by
`outputs/evaluations/week9_monolithic_qwen25_7b_artifact_registry_v1.json`.

## Run Tests

Use Python from the repository root:

```powershell
python -m unittest discover -s tests
```

## Run Example

```powershell
python examples/intent_baseline_example.py
```

## Run Initial Evaluation

```powershell
python scripts/evaluate_intent_baseline.py
```

The evaluation writes raw output to `outputs/evaluations/intent_baseline_roadmap_examples.json`. The included sample is roadmap-derived and synthetic; it is a smoke check, not a research benchmark.
