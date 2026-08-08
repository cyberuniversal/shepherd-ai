# Shepherd-AI Implementation Plan

## Planning Basis

This plan converts `docs/roadmap.pdf` into development milestones and incorporates design cautions from the literature-review export. The requested `docs/roadmap/` directory is not present; the roadmap source is the PDF.

## Milestone 0: Repository Foundation And Project Understanding

Objective: Establish a reproducible Python repository foundation and document the project scope before implementing modules.

Relevant roadmap section: Week 1, "Environment Setup and Repository Exploration."

Relevant literature findings: Related systems should clearly separate planned capabilities from implemented capabilities and should document architecture, assumptions, and evaluation boundaries.

Inputs and outputs: Inputs are `AGENTS.md`, the roadmap PDF, and the literature-review Markdown files. Outputs are project synthesis, implementation plan, README, package structure, test structure, dataset/output directories for the first milestone, and environment notes.

Dependencies: Python is required. Exact Python version and package pins are not stated in the roadmap.

Deliverables: `docs/project_synthesis.md`, this plan, `README.md`, `.gitignore`, `pyproject.toml`, `src/`, `tests/`, `datasets/commands/`, and `outputs/evaluations/`.

Tests: Repository import test and unit-test discovery once code exists.

Evaluation metrics: Not applicable beyond reproducibility checks.

Completion criteria: The repository documents its scope, setup, source documents, known missing details, and first implementable milestone.

Known uncertainties: Exact dependency manager, package versions, CI, notebook style, and formal architecture diagram are not stated.

## Milestone 1: Typed Command Intent Extraction Baseline

Objective: Convert typed mission commands into a bounded JSON mission-intent representation.

Relevant roadmap section: Week 2, "Speech Recognition and Intent Extraction"; specifically typed commands and JSON fields for action, number of drones, location, target, and constraints.

Relevant literature findings: TACOS, Swarm-Steward, CommandSwarm, PROGPROMPT, and the PDDL-goal paper support bounded representations and deterministic validation. They also warn that format-valid output is not the same as task success.

Inputs and outputs: Input is a typed command string. Output is a serializable intent with action, count, location, target, constraints, source text, parser name, and notes.

Dependencies: Python standard library only for the baseline. Whisper, spaCy, and Hugging Face Transformers are planned but not required for this baseline.

Deliverables: Intent schema, deterministic parser, tests, roadmap-derived sample command data, example script, and raw evaluation output.

Tests: Unit tests for supported roadmap commands, empty input handling, JSON serialization, and sample-data evaluation.

Evaluation metrics: Exact-match field accuracy on a small roadmap-derived sample. This is a smoke evaluation, not a research result.

Completion criteria: All tests pass, example command produces JSON, and raw evaluation output is written separately under `outputs/evaluations/`.

Known uncertainties: The roadmap does not specify an intent ontology, parser model, package versions, audio data, transcript format, train/test split, acceptance thresholds, or how to represent missing counts and constraints. Audio support is therefore deferred.

## Milestone 2: Speech-To-Text Input

Objective: Add audio command ingestion and transcript generation using Whisper.

Relevant roadmap section: Week 2 speech recognition tasks and example WAV files with transcripts.

Relevant literature findings: CommandSwarm and the bilingual UAV-control paper show that speech front ends need latency, language, noise, and transcript-quality evaluation. Speech accuracy should not be assumed from model output alone.

Inputs and outputs: Inputs are WAV files and transcript metadata. Outputs are transcripts and linked intent records.

Dependencies: Whisper and an audio-processing environment. Exact package/version choices are not stated.

Deliverables: Audio dataset manifest, transcript format, speech-to-text script/notebook, tests for manifest handling, documented model configuration, and raw Whisper prediction/evaluation artifacts.

Tests: File-format validation, transcript loading, and deterministic behavior for cached transcripts.

Evaluation metrics: Speech-recognition exact-match accuracy and word error rate when a labeled transcript set exists.

Completion criteria: A documented sample-audio workflow produces transcripts reproducibly without private data or credentials.

Current status: A Whisper `base` ASR run has been recorded on a local `NVIDIA GeForce GTX 1650 SUPER` GPU with `--no-fp16`, producing pooled exact-match accuracy `0.9` and mean word error rate `0.01` on the 10-record sample-audio manifest. A retrospective seed-17 split summary now reports 6 train, 2 validation, and 2 test records.

Current handoff status: Week 2 has a development handoff for Week 3 grounding in `reports/week2_to_week3_nlp_handoff.md` and `outputs/evaluations/week2_to_week3_nlp_handoff.json`. The provisional primary intent path is `deterministic_v3`, with 30 / 30 exact intent matches on human/reference transcripts and 27 / 30 exact intent matches on Whisper transcripts for the `audio_v2_holdout` diagnostic benchmark. This is not a clean final benchmark because `deterministic_v3` was developed after inspecting v2 holdout errors. The imported Colab/T4 transformer span path remains active research debt rather than the Week 3 primary handoff path.

Known uncertainties: The current audio split was assigned after the first pooled ASR result existed, so it is not a clean final held-out benchmark. A pre-registered audio split for newly collected recordings and an acceptance threshold are still not specified. The Colab/T4 ASR run is still not recorded because the WAV files are intentionally not tracked in the public repository and therefore are unavailable to a clean Colab clone.

## Milestone 3: Command Grounding And Map Representation

Objective: Map human location terms into coordinates from a custom map dataset.

Relevant roadmap section: Week 3, "Command Grounding and Map Representation."

Relevant literature findings: VLMaps and GeoText-1652 show that language grounding is hard and should not be treated as solved by retrieval or semantic mapping alone.

Inputs and outputs: Inputs are parsed intents and a CSV or GeoJSON map. Outputs are grounded locations and map visualizations.

Dependencies: Pandas and Folium are planned by the roadmap.

Deliverables: Map dataset, grounding module, interactive map visualization, and tests for known terms.

Tests: CSV/GeoJSON validation, exact grounding of known regions, and graceful handling of ambiguous or missing terms.

Evaluation metrics: Grounding accuracy on a labeled command/location set.

Completion criteria: Multiple example commands ground to documented coordinates with provenance.

Known uncertainties: The actual map area, coordinate system, ambiguity policy, and evaluation set are not stated.

Entry condition from Week 2: consume bounded intent JSON with fields `action`, `count`, `location`, `target`, and `constraints` from `deterministic_v3` as a provisional development interface. Week 3 must not silently invent coordinates for unknown terms and must preserve the source command/transcript and parser metadata in grounding outputs.

Current status: An initial deterministic grounding slice exists. It loads `datasets/maps/shepherd_test_map_v1.csv`, a small GeoJSON Point-feature subset at `datasets/maps/shepherd_test_map_v1.geojson`, and a basic GeoJSON Polygon region fixture at `datasets/maps/shepherd_test_map_regions_v1.geojson`; grounds normalized map names and aliases exactly or when embedded inside bounded intent fields through `src/shepherd_ai/grounding.py`; exports grounded references as planner-facing map objects; exposes `scripts/ground_intent.py`; produces and applies operator-facing clarification reports through `src/shepherd_ai/grounding_clarification.py`, `scripts/create_grounding_clarification_report.py`, and `scripts/apply_grounding_clarification.py`; renders Folium inspection maps through `src/shepherd_ai/map_visualization.py` and `scripts/render_grounding_map.py`; validates map structure through `src/shepherd_ai/map_validation.py` and `scripts/validate_map_dataset.py`; validates grounding dataset labels through `src/shepherd_ai/grounding_dataset.py` and `scripts/validate_grounding_dataset.py`; audits synthetic map coverage through `src/shepherd_ai/grounding_coverage.py` and `scripts/audit_grounding_coverage.py`; runs synthetic development/diagnostic/holdout-style evaluations with `scripts/evaluate_grounding.py`; summarizes readiness through `src/shepherd_ai/week3_status.py` and `scripts/summarize_week3_grounding_status.py`; audits Week 3 completion gates through `src/shepherd_ai/week3_completion.py` and `scripts/audit_week3_completion.py`; and supports human-grounding benchmark collection/finalization through `src/shepherd_ai/week3_human_benchmark.py`, `scripts/create_week3_human_grounding_packet.py`, and `scripts/finalize_week3_human_grounding_packet.py`. The synthetic Week 3 acceptance criteria are defined in `docs/week3_acceptance_criteria.md` and `docs/week3_acceptance_criteria.json`; these criteria are explicitly not real-world grounding thresholds. The real/public map provenance deferral is defined in `docs/week3_research_deferrals.md` and `docs/week3_research_deferrals.json`. The human-grounding benchmark protocol is defined in `docs/week3_human_grounding_benchmark_protocol.md`; the current filled packet is `reports/week3_human_grounding_packet.jsonl` and `reports/week3_human_grounding_packet.md`; the finalized benchmark dataset is `datasets/maps/human_grounding_benchmark_v1.jsonl`. The map schema now includes circular geometry, basic polygon exterior boundaries, operational role, flyability, and clearance metadata for later planner/safety modules. The grounder now surfaces map references inside parsed constraints, such as grounding `avoid the power lines` to obstacle record `obs_power_lines`, but it does not enforce safety. GeoJSON holes, multipolygons, and route/safety geometry remain unimplemented. The current development result is 6 / 6 exact records on `datasets/maps/grounding_examples_v1.jsonl`, recorded in `outputs/evaluations/grounding_examples_v1.json`. The current diagnostic result is 5 / 5 exact records on `datasets/maps/grounding_diagnostics_v1.jsonl`, recorded in `outputs/evaluations/grounding_diagnostics_v1.json`; its ambiguous `road` labels now explicitly record candidate IDs. The current synthetic holdout-style result is 20 / 20 exact records and 44 / 44 reference matches on `datasets/maps/grounding_holdout_synthetic_v1.jsonl`, recorded in `outputs/evaluations/grounding_holdout_synthetic_v1.json`; this is synthetic evidence over the same custom map, not real-world grounding accuracy. The current human-written grounding benchmark result is 22 / 22 exact records and 22 / 22 reference matches on `datasets/maps/human_grounding_benchmark_v1.jsonl`, recorded in `outputs/evaluations/human_grounding_benchmark_v1.json`; this is human-written command evidence over the custom synthetic map, not real-world map evidence. The current grounding dataset validation outputs are `outputs/evaluations/grounding_examples_v1_validation.json`, `outputs/evaluations/grounding_diagnostics_v1_validation.json`, `outputs/evaluations/grounding_holdout_synthetic_v1_validation.json`, and `outputs/evaluations/human_grounding_benchmark_v1_validation.json`. The current synthetic main-map coverage output is `outputs/evaluations/grounding_map_coverage_v1.json`, covering 20 / 20 main synthetic map records and all map roles across 31 synthetic dataset records and 66 expected references. The current completion-gate output is `outputs/evaluations/week3_completion_gate_audit.json`: synthetic roadmap gates, synthetic acceptance thresholds, real/public map deferral, and the human-written grounding benchmark gate pass, so advancement is true under the current Week 3 synthetic-map scope. The current main map validation report records 20 locations, 1 restricted record, 1 obstacle record, and 1 expected ambiguous-alias warning. The current region GeoJSON validation report records 3 locations, 2 polygon records, 1 circle record, 1 restricted record, and 0 warnings. Clarification examples now block planning for ambiguous `road` and unresolved `red pickup truck` references. The ambiguous-road artifact can be resolved with explicit operator choices, producing `outputs/evaluations/grounding_resolution_ambiguous_road_service_road.json`.

## Milestone 4: Mission Planning

Objective: Convert grounded requests into executable task sequences or graphs.

Relevant roadmap section: Week 4, "Mission Planning."

Relevant literature findings: PDDL-goal translation, PROGPROMPT, TACOS, and CommandSwarm support separating high-level intent from validated executable steps.

Inputs and outputs: Inputs are intents plus grounded coordinates. Outputs are task sequences or graphs.

Dependencies: NetworkX is planned for planning and graphs.

Deliverables: Planner module/notebook, decomposition examples, and mission-flow diagrams.

Tests: Deterministic task decomposition for roadmap scenarios and invalid-input handling.

Evaluation metrics: Plan validity, step coverage, and later end-to-end task success.

Completion criteria: A command such as "Scan the north field" decomposes into documented steps.

Known uncertainties: Exact task vocabulary and success criteria are not stated.

Current status: An initial deterministic Week 4 mission-planning slice exists. It consumes `GroundedIntent` outputs from Week 3 through `src/shepherd_ai/mission_planning.py`, selects a primary grounded map object, preserves all referenced map objects, and emits serializable task sequences plus NetworkX-backed dependency graphs with grounded map IDs, coordinates, expected outputs, issues, and caveat notes. Observation commands now include the roadmap-required steps to capture images, plan a downstream vision-model task, save results, and return. Constraint-bearing commands include an explicit `review_constraints` step before takeoff. The same module now validates the plan contract: status consistency, blocked-plan rules, unique step IDs, backward-only dependencies, required action coverage, map-coordinate presence for map-dependent steps, and required constraint-review coverage. The primary CLI is `scripts/plan_mission.py`; planning evaluation is implemented in `scripts/evaluate_mission_planning.py`; mission-flow diagram rendering is implemented in `scripts/render_mission_flow.py`; completion auditing is implemented in `scripts/audit_week4_completion.py` and `src/shepherd_ai/week4_completion.py`. Current example outputs are `outputs/evaluations/week4_plan_north_field_example.json`, `outputs/evaluations/week4_plan_ambiguous_road_blocked.json`, `outputs/evaluations/week4_plan_constraint_greenhouse_power_lines.json`, and `outputs/diagrams/week4_plan_north_field_flow.md`. Current evaluation over `datasets/maps/human_grounding_benchmark_v1.jsonl` is recorded in `outputs/evaluations/week4_planning_human_grounding_benchmark_v1.json`: 22 records, 20 planned, 2 blocked, 22 / 22 expected plan-status matches, 22 / 22 required action matches, 22 / 22 required issue matches, and 22 / 22 valid plan contracts. Focused planning cases are recorded in `datasets/maps/week4_planning_cases_v1.jsonl` and `outputs/evaluations/week4_planning_cases_v1.json`: 7 records, 5 planned, 2 blocked, 7 / 7 expected plan-status matches, 7 / 7 required action matches, 7 / 7 required issue matches, and 7 / 7 valid plan contracts. Week 4 acceptance criteria are recorded in `docs/week4_acceptance_criteria.json` and `docs/week4_acceptance_criteria.md`; explicit deferrals are recorded in `docs/week4_research_deferrals.json` and `docs/week4_research_deferrals.md`. The completion-gate audit is recorded in `outputs/evaluations/week4_completion_gate_audit.json` and `reports/week4_completion_gate_audit.md`: advancement is allowed, the decision is `week4_complete_for_advancement_to_week5_scheduling`, and blockers are empty. This is a high-level task-sequence planner only. It does not perform scheduling, route optimization, actual computer-vision inference, simulation execution, or safety validation. Restricted, obstacle, and clearance map metadata is preserved as planner issues for later safety work.

## Milestone 5: Multi-Drone Scheduling

Objective: Allocate planned tasks across simulated drones and compare simple strategies.

Relevant roadmap section: Week 5, "Multi-Drone Coordination."

Relevant literature findings: The task-allocation review supports comparing algorithms under common metrics but includes narrative/table conflicts that must be preserved.

Inputs and outputs: Inputs are task plans and simulated drone states. Outputs are assignment tables and strategy comparisons.

Dependencies: Pandas, NumPy, and possibly NetworkX.

Deliverables: Scheduler module/notebook, allocation visualization, and example simulations.

Tests: Assignment consistency, availability handling, and deterministic strategy comparison.

Evaluation metrics: Scheduling quality, completion time/cost proxy, fairness, and response delay if modeled.

Completion criteria: Three simulated drones receive valid assignments for sample missions.

Known uncertainties: Cost function, drone model, battery model, and strategy set are not specified.

Current status: An initial deterministic Week 5 scheduling slice exists. It consumes Week 4 mission-plan payloads through `src/shepherd_ai/scheduling.py`, expands multi-drone commands into schedulable task replicas, loads a simulated three-drone fleet from `datasets/drones/week5_three_drone_fleet_v1.json`, and compares `round_robin`, `least_loaded`, and `nearest_available` assignment strategies. The primary CLI is `scripts/schedule_missions.py`; completion auditing is implemented in `scripts/audit_week5_completion.py` and `src/shepherd_ai/week5_completion.py`. The scheduler notebook is `notebooks/Notebook5_Scheduler.ipynb`. Current outputs are `outputs/evaluations/week5_schedule_comparison_v1.json`, `reports/week5_schedule_comparison_v1.md`, `outputs/tables/week5_assignments_least_loaded.csv`, and `outputs/visualizations/week5_drone_allocation_least_loaded.html`. Week 5 acceptance criteria are recorded in `docs/week5_acceptance_criteria.json` and `docs/week5_acceptance_criteria.md`; explicit deferrals are recorded in `docs/week5_research_deferrals.json` and `docs/week5_research_deferrals.md`. The completion-gate audit is recorded in `outputs/evaluations/week5_completion_gate_audit.json` and `reports/week5_completion_gate_audit.md`. This is a scheduling simulation only. It does not perform route optimization, safety validation, real execution, physical-drone control, or computer-vision inference.

## Milestone 6: Computer Vision Integration

Objective: Run aerial-image inference and save detections.

Relevant roadmap section: Week 6, "Computer Vision Integration."

Relevant literature findings: Vision-language and aerial-ground papers warn that perception demos do not guarantee mission reliability.

Inputs and outputs: Inputs are licensed aerial images. Outputs are detections, confidence values, annotated images, and detection summaries.

Dependencies: Ultralytics YOLO plus dataset-specific tooling.

Deliverables: Vision notebook/module, detection examples, annotated outputs, and summary table.

Tests: Dataset manifest validation and output schema validation.

Evaluation metrics: Detection performance when labeled data exists.

Completion criteria: A documented dataset subset can be processed reproducibly.

Known uncertainties: Dataset selection, license/access notes, labels, splits, and model weights are not yet specified.

Current status: Week 6 is complete for roadmap advancement. Agriculture-Vision
provides the licensed, provenance-tracked semantic-segmentation development
path, including fixed train/validation subsets, negative class-imbalance
results, and a leading fixed-subset BCE-Dice result with modified mIoU
`0.15387`. VisDrone2019-DET provides the labeled YOLO-compatible detection
path. Its registered YOLOv8n run completed 50 epochs on the official training
split and produced validation precision `0.43116`, recall `0.32034`, mAP50
`0.29677`, and mAP50-95 `0.16724` from `best.pt`; test-dev was not used for
selection. The completion evidence is recorded in
`docs/week6_completion_assessment.md` and
`outputs/evaluations/week6_visdrone_yolov8n_seed17_e50_completed_summary.json`.
This completes the roadmap milestone, not the broader research problem:
Agriculture-Vision anomaly performance remains narrow and vision is not yet
integrated into mission execution.

## Milestone 7: Safety, Feedback, And Integration

Objective: Add clarification dialogue, status updates, safety validation, and integrate previous modules.

Relevant roadmap section: Week 7, "Feedback, Safety, and Integration."

Relevant literature findings: TACOS, Swarm-Steward, CommandSwarm, and SkySim support deterministic safety gates and closed-loop monitoring.

Inputs and outputs: Inputs are plans, schedules, drone state, and map constraints. Outputs are safety reports, status updates, and integrated workflow results.

Dependencies: Prior milestones.

Deliverables: Feedback module, safety validator, and integrated prototype.

Tests: Battery, restricted-area, altitude, and availability checks.

Evaluation metrics: Safety-check coverage and rejection of invalid missions.

Completion criteria: Unsafe or incomplete missions are flagged before simulated execution.

Known uncertainties: Battery thresholds, altitude limits, restricted-area dataset, and operator-clarification policy are not stated.

Current status: Week 7 is complete for roadmap advancement after a corrected,
literature-grounded audit. The deterministic
pre-execution development slice in `src/shepherd_ai/safety.py` applies battery,
restricted-area, altitude, and availability checks to every assignment using
the explicit synthetic policy at
`datasets/safety/week7_safety_policy_v1.json`. The integrated workflow reuses
the Week 3 clarification report, Week 4 planner, and Week 5 scheduler, emits
ordered feedback and schedule-based projected status updates, and blocks failed
or unavailable evidence. The registered preflight case matrix and protocol are
`datasets/safety/week7_safety_cases_v1.jsonl` and
`docs/week7_safety_protocol.md`. The registered 12-case evaluation matched all
expected workflow statuses and failed categories. A second development slice in
`src/shepherd_ai/mission_supervision.py` adds explicit confirmation, event-driven
lifecycle states, telemetry-triggered safety rechecks, pause/resume/cancel,
low-battery return requests, and availability-loss hold/replan requests. Its six
registered synthetic cases match their expected final states, event sequences,
and interventions. The final evidence also includes a four-case stateful
clarification evaluation, three route-geometry cases over circles and polygons,
eight supervision cases including a multi-snapshot safe-to-unsafe separation
transition, three prior-module integration cases covering typed input, a stored
Whisper prediction, the selected deterministic parser, the trained Naive Bayes
intent interface, and a bounded Week 6 vision-result binding, plus sensitivity
analysis over four synthetic policy dimensions. The corrected completion audit
permits Week 8 advancement with no blockers. This remains software-simulation
evidence and does not establish mission-specific vision, continuous dynamics,
active collision avoidance, or physical safety. See `docs/week7_gap_audit.md`.

## Milestone 8: End-To-End Demonstration And Evaluation

Objective: Run the full scenario from the roadmap and evaluate the complete system.

Relevant roadmap section: Week 8, "End-to-End Demonstration and Experimental Evaluation."

Relevant literature findings: Similar papers often overstate format validity; Shepherd-AI should measure actual module and workflow success.

Inputs and outputs: Inputs are command/audio data, maps, drone states, imagery, and safety constraints. Outputs are mission reports, logs, screenshots, and evaluation results.

Dependencies: Milestones 1 through 7.

Deliverables: Complete prototype, evaluation results, screenshots/logs, and organized source repository.

Tests: End-to-end scenario test and module regression tests.

Evaluation metrics: Intent extraction accuracy, grounding accuracy, scheduling quality, detection performance, and overall execution time.

Completion criteria: The roadmap scenario executes reproducibly and produces documented results without fabricated data.

Known uncertainties: Acceptance thresholds and baseline comparisons are not stated.

Current status: Week 8 is complete for roadmap advancement. The exact fixed
scenario was run through registered human audio, Whisper ASR, the frozen
expanded85 DistilBERT intent checkpoint, map grounding, three-drone scheduling,
deterministic safety validation and simulation, and frozen Agriculture-Vision
segmentation inference. The stored results are WER `0.07143`, intent exact
match `1/2` and field accuracy `9/10`, grounding accuracy `2/2`, scheduling
completion `3/3`, mission-class modified mean IoU `0.02356` over 59 images, and
`31.3343` seconds of measured warm-model pipeline time. The completion audit
passes all ten gates with no blockers. The vision result is weak and must not
be hidden by the successful orchestration result. This is one development
scenario in software simulation; it is not physical-flight evidence, a safety
guarantee, a statistical end-to-end benchmark, or an established novelty claim.
The optional 3D experiments remain discontinued historical negative evidence.

## Milestone 9: Research Paper Draft

Objective: Convert the implemented prototype and evaluation into a manuscript draft.

Relevant roadmap section: Week 9.

Relevant literature findings: Claims must separate related-work results from Shepherd-AI results and preserve limitations.

Inputs and outputs: Inputs are implemented architecture, experiment logs, figures, and literature notes. Outputs are paper sections, figures, tables, citations, and bibliography.

Dependencies: Evaluation artifacts from Milestone 8.

Deliverables: First research-paper draft, system figures, tables, and organized bibliography.

Tests: Citation/source audit and result traceability review.

Evaluation metrics: Not a system metric; documentation completeness and traceability.

Completion criteria: Draft sections exist and all claims trace to source documents or experiments.

Known uncertainties: Target venue/style and final contribution are not stated.

Current status: Week 9 is complete for roadmap advancement. The first draft is
`reports/shepherd_ai_paper_draft.md`; it includes every roadmap-required draft
section and explicitly separates literature findings, implemented behavior,
measured Shepherd-AI results, and unsupported claims. The organized working
bibliography covers all 15 papers in the repository review. A tested evidence
builder validates the completed Week 8 audit and claim-limit flags before
generating the five-metric table, runtime table and figure, architecture and
evaluation workflow diagrams, source hashes, and traceability report. Notebook
9 reproduces these artifacts without rerunning training or consuming a GPU.
The Week 9 completion audit passes all eight gates with no blockers. This is a
complete first-draft milestone, not a final manuscript or publication-readiness
claim; venue style, formal research question, and novelty remain unspecified.

Post-draft evidence strengthening: The 38-case Qwen diagnostic is preserved but
reuses development evidence. A fresh held-out result is still not evaluated.
The repository now implements the collection and governance workflow in
`docs/human_evidence_benchmark_protocol.md`: exact frozen-context hashing,
label-blinded independent review, mandatory third-party adjudication of
disagreements, overlap and class-balance validation, and label-separated model
packet construction. Actual commands, human identities, reviews, and labels
remain uncollected and are not fabricated by the tooling.

## Milestone 10: Final Paper And Presentation

Objective: Finalize manuscript, documentation, slides, and demo materials.

Relevant roadmap section: Week 10.

Relevant literature findings: Limitations, failed experiments, and negative results should be preserved.

Inputs and outputs: Inputs are final evaluation artifacts and draft paper. Outputs are final paper, slides, source package, README, and demo materials.

Dependencies: All prior milestones.

Deliverables: Final research paper, presentation slides, complete documentation, source package, and demo materials.

Tests: Reproducibility pass over documented commands.

Evaluation metrics: Completeness of final reporting and reproducibility.

Completion criteria: Documentation and artifacts are suitable for the intended student research/demo setting.

Known uncertainties: Formatting requirements and dissemination target are not stated.

## Post-Roadmap Research Revision: MultiUAV-Plat Validation Placement

Objective: Replace the active paper claim with a bounded
systems-and-measurement study of how validation placement changes failure
containment and safety-utility-compute trade-offs in local multi-UAV planning.

Relevant roadmap section: This refines Week 9 evaluation design and Week 10
paper finalization. It is not an additional completed roadmap week.

Relevant literature findings: Hierarchical language-robot systems repeatedly
separate semantic planning from deterministic tools, safety gates, execution,
and monitoring. Format validity does not establish mission correctness, and
raw failures and negative results must be retained.

Inputs and outputs: The planned input is an immutable MultiUAV-Plat source
release plus five matched variants per source task. Outputs are label-separated
datasets, four method configurations, raw predictions, containment labels,
joint decision/fidelity/resource metrics, clustered statistical analysis, and
a revised manuscript.

Dependencies: Verified upstream commit and archive hash; locally reproduced
source counts; registered intervention, split, review, model-call, offline, and
hardware protocols; immutable Qwen model commits; and tested validators.

Deliverables: See `docs/multiuav_validation_study_protocol.md`.

Tests: Source-manifest integrity, full-cluster split enforcement, prompt
leakage, trained-component wiring, strict output parsing, recursive plan
grounding, call-budget parity, checkpoint compatibility, raw-result
completeness, and publication-summary isolation.

Evaluation metrics: Unsafe execution, silent continuation, false
non-execution, decision accuracy, plan validity and fidelity, failure
containment stage, latency, tokens, model calls, RAM, VRAM, and GPU-board
energy.

Completion criteria: The registered protocol is frozen before final scoring;
every expected method-case row and failure is retained; analysis is clustered
by source task; all claims trace to stored evidence; and the conclusion follows
the observed result.

Current status: The frozen 3B and 7B deterministic accuracy runs are complete,
with 5,680 retained method-case rows per model. Both sealed matrices passed the
score-blind admission gate in
`datasets/multiuav_plat/accuracy_matrix_admission_v1.json`; no hidden labels or
study outcomes were accessed at admission. Registered label-separated scoring
has now completed for all 11,360 rows, with derived row archives separated from
the aggregate summary. All eight registered source-cluster bootstrap analyses
have also completed with 10,000 fixed-seed draws each. Accuracy figure
generation is complete in both PNG and PDF formats, with exact CSV source rows
and a source-hashed provenance manifest. The separate resource experiment
remains pending.

Known uncertainties: Hardware measurement controls and the later resource
repetitions remain unresolved. Call budgets, recoverability rules, static
execution scope, source provenance, split registration, official alias
authority, task eligibility, reviewer provenance, and the exclusion of the
existing DistilBERT span tagger from the primary comparison are frozen with
their documented limitations.
