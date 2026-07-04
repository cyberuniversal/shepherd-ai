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

Deliverables: Audio dataset manifest, transcript format, speech-to-text script/notebook, tests for manifest handling, and documented model configuration.

Tests: File-format validation, transcript loading, and deterministic behavior for cached transcripts.

Evaluation metrics: Speech-recognition accuracy when a labeled transcript set exists.

Completion criteria: A documented sample-audio workflow produces transcripts reproducibly without private data or credentials.

Known uncertainties: The repository now has 10 self-recorded WAV records, all marked `train`; a final audio train/validation/test split, Whisper version, and acceptance threshold are still not specified.

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
