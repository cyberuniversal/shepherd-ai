# Shepherd-AI Agent Instructions

This file governs work in the Shepherd-AI repository. Do not treat planned roadmap items as implemented code.

## Mandatory Source Documents

Before making architectural, research, dataset, evaluation, roadmap, or implementation decisions, read:

- `D:\Users\momoa\Desktop\shepherd-ai\docs\roadmap.pdf`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\literature_review\ExportBlock-44375080-06b3-45d5-a3ed-ac880ba80cd6-Part-1.zip`
- Every Markdown file inside that literature-review export, including each paper page and its `Complete Summary ...md`.
- `D:\Users\momoa\Desktop\shepherd-ai\docs\literature_to_implementation.md`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\code_plan_compliance.md`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\source_material\code_plan_2026-07-25.docx`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\multiuav_validation_study_protocol.md`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\multiuav_recoverability_protocol.md`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\multiuav_intervention_pilot_protocol.md`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\multiuav_intervention_review_protocol.md`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\multiuav_intervention_feedback_resolution.md`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\multiuav_grounding_validator_protocol.md`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\multiuav_model_revisions.md`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\multiuav_runner_checkpoint_protocol.md`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\multiuav_method_contract.md`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\multiuav_offline_runtime_protocol.md`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\multiuav_statistical_analysis_protocol.md`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\multiuav_execution_scope_protocol.md`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\multiuav_hardware_measurement_protocol.md`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\multiuav_resource_analysis_protocol.md`
- `D:\Users\momoa\Desktop\shepherd-ai\docs\multiuav_qwen_cache_smoke.md`

The user mentioned `docs/roadmap/`, but the repository currently contains `docs/roadmap.pdf`, not a `docs/roadmap/` directory. Do not silently rewrite that path in future reports; note the mismatch if it matters.

## Active Paper Direction

The active paper direction is the proposed MultiUAV-Plat validation-placement
study in `docs/multiuav_validation_study_protocol.md`. It supersedes the prior
evidence-aware paper direction but does not erase its implementation, raw
outputs, or negative evidence.

The locked 3B and 7B accuracy matrices, score-blind admission, deterministic
scoring, registered source-cluster bootstrap, and publication figures are now
stored. Treat only those preserved accuracy artifacts as admitted study
results. Resource campaign attempt 3 completed all 24 conditions and 3,600 rows
on one RTX 3090, passed score-blind admission, and has now completed the
registered secondary resource analysis. Treat only the preserved summary,
safe derived rows, bootstrap evidence, exact source tables, figures, and
provenance manifest as resource findings. Attempt 2's partial raw rows, frozen
contracts, and synthetic tooling probes are not resource findings. In
particular:

- cite the locally reproduced 75 sessions, 1,500 tasks, and 9,396 checks only
  through `datasets/multiuav_plat/source_audit_v1.json`;
- distinguish the 7,500 pre-exclusion design from the deterministically
  validated 7,365-case controlled-derivative dataset;
- describe the 30-cluster, 150-case expert-reviewed pilot as sampled
  construction QC, not full row-level human labeling or final evaluation data;
- describe M4 as compute matched only at the registered model-call-budget
  level; do not imply matched latency, memory, or energy before the resource
  experiment;
- preserve the registered exclusion of DistilBERT from M1-M4 because its
  historical Shepherd intent-span role is not MultiUAV API planning;
- do not label a missing-fact case `CLARIFY` when allowed observation APIs can
  recover the fact;
- do not label a resource-conflict case `BLOCK` when a valid UAV or recovery
  action remains;
- do not expose hidden validators, official reference plans, or privileged
  state to any evaluated model; and
- do not describe static plan checks as live simulator mission success.
- treat `datasets/multiuav_plat/grounding_contract_audit_v1.json` as a
  deterministic contract integrated into M2-M4 and externally reapplied to all
  methods by the frozen scorer. Cite evaluated containment only through the
  admitted scoring and bootstrap artifacts, not through the contract audit.
- treat immutable model revision resolution as metadata verification only.
  Separate artifacts now prove that the pinned 3B and 7B checkpoints were
  cached, checksummed, loaded, and invoked on synthetic fixtures; they do not
  alter the meaning of the revision audit or establish study evaluation.
- do not run `pending_human_review` cases through a model backend; the runner
  status gate permits only approved evaluation cases or explicit synthetic
  unit fixtures.
- use the corrected training-only `intervention_pilot_v2.json` and compact
  per-case review packet. Version 1 is superseded diagnostic evidence. Keep
  calibration/test cases out of template debugging, and keep known-bad
  validator probes separate from study and review data.
- cite checkpoint cache/load events only through the corresponding
  `qwen25_3b_*_v1.json` and `qwen25_7b_*_v1.json` artifacts under
  `datasets/multiuav_plat/`. Both current smokes used synthetic fixtures and
  produced one-token, uninterpreted outputs. The historical 32-token 3B smoke
  remains separately preserved. One approved row was invoked in an aborted
  local feasibility attempt; preserve it under `failed_attempts/`, disclose the
  raw-output inspection deviation, and exclude it from every study result.
- treat the primary evaluation scope as static plan fidelity under
  `datasets/multiuav_plat/execution_scope_audit_v1.json`; do not call static
  API, parameter, or official-command checks live mission success.
- treat `datasets/multiuav_plat/scoring_contract_audit_v1.json` as score-blind
  method infrastructure. It read no study checkpoint rows. Preserve raw model
  decisions separately from post-gate system disposition, and never expose
  hidden official command labels to model prompts.
- treat `hardware_measurement_contract_audit_v1.json` as a synthetic tooling
  probe only. It implements method-case telemetry and is not a study energy
  result. `resource_schedule_v1.json` is the final approved 30-cluster,
  150-case, 24-condition schedule, and
  `resource_hardware_protocol_v1.json` freezes the RTX 3090, warm-up, thermal,
  process-isolation, and invalid-row controls. Neither artifact is a run config
  or result. All 24 attempt-3 configs are bound to the cooldown-aware execution
  revision. Preflight v3 independently verified both frozen model artifacts and
  exact-GPU NVML capabilities without loading a model or starting measurement.
  Campaign attempt 3 completed all 24 conditions, passed score-blind resource
  admission, and completed the registered separate-repetition aggregate
  analysis. Resource results are secondary and exploratory. Cite them through
  `outputs/evaluations/multiuav_resource_analysis_v1/summary.json`, the exact
  source tables, and `docs/multiuav_resource_analysis_protocol.md`. Disclose
  the preserved one-row post-admission raw-output inspection deviation. Do not
  pool repetitions or reinterpret intervals as unregistered significance tests.

The old `reports/shepherd_ai_paper_draft.md`, 38-case diagnostic, Qwen
diagnostic, and fresh-human benchmark tooling are historical artifacts. They
are not results for the new paper.

## Roadmap Versus Literature Review Authority

Use the roadmap as high-level project sequencing only: which week/milestone comes next, what broad deliverables are expected, and which technology families are planned.

Use the literature review for technical implementation decisions: architecture boundaries, model-training expectations, validation strategy, dataset discipline, grounding design, planner/scheduler boundaries, safety rules, and evaluation interpretation.

If the roadmap sounds like a simple demo but the literature review shows that a hand-written, zero-shot, or untrained approach would be weak, follow the literature review. For example:

- Week 2 intent extraction should not stop at a hand-written parser. Build labeled command data, define splits, train or fine-tune an intent extraction model when enough labels exist, and compare against a deterministic baseline.
- Whisper can be used for speech-to-text, but ASR evaluation must be separate from intent extraction evaluation.
- LLMs may propose structured plans or translations, but deterministic validators and conventional planners/controllers must gate execution.
- Any trained or fine-tuned model requires recorded data provenance, split definitions, random seeds, package/model versions, parameters, raw outputs, and held-out evaluation.

For the active MultiUAV validation-placement study, the source code plan
defines the build order, locked protocol, and definition of done. Track every
requirement explicitly in `docs/code_plan_compliance.md`; do not skip an
unimplemented gate, start the full GPU experiment before correctness gates
pass, or interpret a wiring smoke test as paper evidence.

## Current Repository Status

At the time this file was created, the repository was documentation-only. Always inspect the current repository tree before describing implementation status. Initially it contained:

- `docs/roadmap.pdf`
- `docs/literature_review/ExportBlock-44375080-06b3-45d5-a3ed-ac880ba80cd6-Part-1.zip`
- This root-level `AGENTS.md`

At creation time there was no source code, no README, no package/environment file, no notebooks, no datasets, no experiments, no tests, and no lint or format configuration in the repository. The repository has since started adding source, tests, docs, and Colab notebook structure. Always inspect current files before making status claims.

## What Shepherd-AI Is

The roadmap gives the tentative project title as "Natural Language Multi-Drone Mission Planning and Coordination using Shepherd-AI." The goal is a research prototype in which an operator can issue voice or text commands, such as sending multiple drones to inspect crops and irrigation, and the software pipeline turns those commands into simulated multi-drone missions.

The roadmap states that the project is implemented as a software simulation using Python and publicly available datasets. It explicitly says no physical drone hardware is required. Treat physical-drone papers in the literature review as background evidence, not as implemented Shepherd-AI hardware requirements.

## Intended Goals And Scope

Roadmap-supported goals:

- Convert speech to text.
- Extract mission intent from typed or spoken commands.
- Ground vague commands into map locations.
- Plan executable drone tasks.
- Coordinate multiple virtual drones.
- Analyze images using computer vision.
- Validate safety constraints.
- Generate mission feedback and reports.
- Produce evaluation results, figures, documentation, and a research-paper draft/final version.

Current scope is a Python software prototype and simulation. The active study
has a proposed research question and bounded systems-and-measurement
contribution in `docs/multiuav_validation_study_protocol.md`. Its accuracy
protocol and registered analyses are complete, but the separate resource
experiment and final paper conclusion remain unresolved. Do not extend the
observed static, controlled-derivative results to physical flight or general
model-family claims.

## Planned Pipeline And Modules

The roadmap proposes this pipeline:

1. Speech or typed command input.
2. Speech recognition using Whisper for audio.
3. Intent extraction into JSON fields such as action, drone count, location, target, and constraints.
4. Command grounding from human terms such as `north`, `greenhouse`, or `irrigation canal` to coordinates in a custom map dataset.
5. Mission planning that decomposes a request into steps such as takeoff, fly to destination, capture images, run vision, save results, and return.
6. Multi-drone scheduling/allocation across simulated drones, initially with simple scheduling logic and strategy comparison.
7. Computer-vision inference on aerial imagery, planned around Ultralytics YOLO.
8. Safety validation for battery threshold, restricted areas, altitude limits, and drone availability.
9. Feedback/status updates, clarification dialogue, integration, and final reports.
10. Evaluation and research-paper preparation.

Roadmap modules now have mixed implementation status. Inspect source, tests,
acceptance audits, and `docs/code_plan_compliance.md` before describing any
module as planned, implemented, evaluated, or complete.

## Planned Technology Stack

The roadmap lists the intended stack:

- Development platforms: Google Colab, Jupyter Notebook, or VS Code.
- Language: Python.
- Version control: Git and GitHub.
- NLP: Hugging Face Transformers and spaCy.
- Speech recognition: Whisper.
- Computer vision: Ultralytics YOLO.
- Planning and graphs: NetworkX.
- Visualization: Matplotlib and Folium.
- Data processing: Pandas and NumPy.

`pyproject.toml` declares the current Python dependency ranges and optional
vision dependencies. Derive install, test, lint, format, and run commands from
current repository configuration rather than inventing them.

## Current Week 8 Simulation Decision

The user discontinued the Gazebo and Three.js work on 2026-07-21. The active
Week 8 simulator is the roadmap-supported Python software simulation with
deterministic telemetry and Folium visualization. Do not resume or rebuild a 3D
simulator unless the user explicitly reverses this decision.

The discontinued 3D experiment reports remain historical negative evidence.
They are not active architecture, dependencies, roadmap requirements, or Week 8
completion evidence. Mission imagery must come from an explicitly registered
mission image manifest; prior development images or abandoned simulator frames
must not be silently relabeled as mission observations.

## Planned Data And Experiments

The roadmap proposes, but does not yet provide, these data locations:

- `datasets/maps/`
- `datasets/aerial_images/`
- `datasets/sample_audio/`
- `datasets/commands/`
- `outputs/`
- `reports/`
- `src/`
- `notebooks/`

Planned datasets include self-recorded WAV commands with transcripts, custom CSV or GeoJSON mission locations, and public imagery datasets such as VisDrone, UAVDT, DOTA, xView, and Agriculture-Vision. The repository now contains curated metadata and benchmark artifacts, while licensed pixels, audio, model weights, and upstream benchmark archives may remain local or private. When adding data, record source, license/access notes, preprocessing steps, and train/test/evaluation splits in documentation.

Roadmap evaluation metrics are:

- Intent extraction accuracy.
- Grounding accuracy.
- Scheduling quality.
- Detection performance.
- Overall execution time.

Do not add paper-specific metrics from the literature review as Shepherd-AI metrics unless an experiment explicitly adopts them.

## Literature Review Lessons

The literature review supports these design cautions:

- LLMs should act as high-level interpreters, planners, or translators, not low-level flight controllers.
- Use bounded, inspectable representations such as JSON mission specs, trusted APIs, PDDL-style goals, behavior trees, or validated tool calls instead of arbitrary generated Python for safety-critical execution.
- Deterministic validators, safety checks, and conventional planners/controllers should handle execution, geometry, allocation, collision avoidance, and safety constraints.
- Hierarchical designs recur across TACOS, Swarm-Steward, CommandSwarm, PROGPROMPT, GenSwarm, and the aerial-ground papers: separate semantic interpretation from execution monitoring and low-level control.
- Closed-loop monitoring matters: plans should be checked against current state, unfinished work, drone availability, failures, and new operator instructions.
- Classical task allocation remains important. The task-allocation review suggests using algorithm choice based on mission conditions rather than letting an LLM manually assign every target.
- Semantic grounding and mapping are difficult. VLMaps, GeoText-1652, and the aerial-ground papers are relevant to grounding language in maps or imagery, but none should be treated as a solved Shepherd-AI module.
- Vision and language systems often show promising demos but limited reliability; distinguish format-valid output from actual task success.
- Simulation results and physical-robot results are not interchangeable.

## Colab-First Project Structure

Maintain the Google Colab-style structure from the roadmap:

- `notebooks/Notebook1_Setup.ipynb`
- `notebooks/Notebook2_NLP.ipynb`
- `notebooks/Notebook3_Grounding.ipynb`
- `notebooks/Notebook4_Planner.ipynb`
- `notebooks/Notebook5_Scheduler.ipynb`
- `notebooks/Notebook6_Vision.ipynb`
- `notebooks/Notebook7_Safety.ipynb`
- `notebooks/Notebook8_FinalDemo.ipynb`
- `notebooks/Notebook9_Evaluation.ipynb`
- `datasets/commands/`
- `datasets/sample_audio/`
- `datasets/maps/`
- `datasets/aerial_images/`
- `outputs/`
- `reports/`
- `src/`
- `tests/`

Notebooks should orchestrate experiments and show reproducible Colab workflows. Shared logic belongs in `src/shepherd_ai/`, not duplicated across notebooks.

Notebook outputs must not be used as evidence unless the raw output files, data inputs, model versions, parameters, and split definitions are committed or documented.

For Week 2 Hugging Face transformer fine-tuning, use Google Colab with a T4 GPU runtime. Do not silently run transformer fine-tuning on local CPU. Local development may run lightweight validation, export, deterministic baselines, dependency-free baselines, and tests.

## Facts, Plans, And Hypotheses

Use these labels in documentation and code comments when relevant:

- Fact: At the time this AGENTS.md file was created, the repository had documentation only; inspect the current tree before making status claims.
- Fact: The roadmap defines a Python simulation prototype, not physical drone deployment.
- Fact: The literature review covers multi-drone coordination, natural-language robotics, task allocation, semantic maps, behavior trees, voice control, and aerial-ground systems.
- Planned work: notebooks/modules for setup, NLP, grounding, planning, scheduling, vision, safety, integration, evaluation, and paper writing.
- Untested hypothesis: the planned modules can be integrated into a working end-to-end Shepherd-AI prototype with useful evaluation results.
- Currently unresolved for the active study: external scientific/manuscript
  review, venue selection, venue-formatted bibliography, and final submission
  review. The accuracy and resource runs, admission gates, registered analyses,
  source tables, figures, integrated draft, 25-check/22-artifact internal
  traceability audit, and hash-bound unreviewed external-review packet are
  complete. No external review has been received. Do not replace commit-bound
  evidence with ad hoc model invocation or manually copied values, and do not
  mark the review packet approved without a real reviewer response.

## Known Conflicts And Caveats

- The user-requested `docs/roadmap/` path does not exist; the roadmap is `docs/roadmap.pdf`.
- The roadmap is a project plan for a software simulation, while many literature-review papers discuss physical robots. Do not turn those papers into Shepherd-AI requirements unless the roadmap or later project docs say so.
- Literature-review paper #12 reports task-allocation tables that conflict with some of its narrative claims. For example, the narrative says Hungarian consistently has the lowest static cost, while the extracted tables show auction lower in some medium/large static settings. Preserve this caveat when using that paper.
- Some reviewed works are not swarm mission planners: GeoText-1652 is an aerial image-text retrieval benchmark, VLMaps is primarily single-robot semantic navigation, and several papers are single-drone or voice-command systems. Use them only for the relevant lesson.

## Coding And Documentation Practices

- Follow the roadmap sequence unless the user explicitly changes priority, but use the literature review for how each milestone should be technically implemented.
- Keep code and notebooks aligned with the planned project structure from the roadmap.
- Treat data, outputs, reports, and experiments as first-class artifacts; document provenance and evaluation settings.
- Add tests only when there is code to test, and derive commands from actual repository configuration.
- If creating notebooks, keep them reproducible and document required inputs/outputs.
- If creating Python modules, keep interfaces explicit and serializable where possible, especially for mission intents, grounded locations, plans, schedules, detections, safety reports, and mission reports.
- If adding dependencies or commands, commit the supporting config files or document the environment clearly.
- Prefer trainable, evaluated components where the literature shows that rules or zero-shot prompts are insufficient. Keep simple deterministic baselines for comparison.
- Do not call a scaffold, wrapper, cached transcript flow, or hand-written baseline a trained model.
- Do not claim a milestone is complete if its literature-supported training, validation, data, or evaluation requirements are missing.

## Do Not Claim Or Implement Without Evidence

Do not claim any of the following unless supported by repository code, datasets, or updated project documents:

- That Shepherd-AI already has a working end-to-end prototype.
- That any specific module, dataset, benchmark, model, or evaluation result exists.
- That the system controls physical drones.
- That safety is guaranteed.
- That LLM outputs are correct, verified, or safe by default.
- That a literature-review result is a Shepherd-AI result.
- That a planned public dataset has been downloaded, licensed, or preprocessed.
- That there is a supported test/lint/format command.
- That the formal research question or scientific contribution has been finalized.

When important details are missing, state that they are currently unspecified and point to the source documents that were checked.
