# Shepherd-AI Agent Instructions

This file governs work in the Shepherd-AI repository. Do not treat planned roadmap items as implemented code.

## Mandatory Source Documents

Before making architectural, research, dataset, evaluation, roadmap, or implementation decisions, read:

- `C:\Users\momoa\Desktop\shepherd-ai\docs\roadmap.pdf`
- `C:\Users\momoa\Desktop\shepherd-ai\docs\literature_review\ExportBlock-44375080-06b3-45d5-a3ed-ac880ba80cd6-Part-1.zip`
- Every Markdown file inside that literature-review export, including each paper page and its `Complete Summary ...md`.
- `C:\Users\momoa\Desktop\shepherd-ai\docs\literature_to_implementation.md`

The user mentioned `docs/roadmap/`, but the repository currently contains `docs/roadmap.pdf`, not a `docs/roadmap/` directory. Do not silently rewrite that path in future reports; note the mismatch if it matters.

## Roadmap Versus Literature Review Authority

Use the roadmap as high-level project sequencing only: which week/milestone comes next, what broad deliverables are expected, and which technology families are planned.

Use the literature review for technical implementation decisions: architecture boundaries, model-training expectations, validation strategy, dataset discipline, grounding design, planner/scheduler boundaries, safety rules, and evaluation interpretation.

If the roadmap sounds like a simple demo but the literature review shows that a hand-written, zero-shot, or untrained approach would be weak, follow the literature review. For example:

- Week 2 intent extraction should not stop at a hand-written parser. Build labeled command data, define splits, train or fine-tune an intent extraction model when enough labels exist, and compare against a deterministic baseline.
- Whisper can be used for speech-to-text, but ASR evaluation must be separate from intent extraction evaluation.
- LLMs may propose structured plans or translations, but deterministic validators and conventional planners/controllers must gate execution.
- Any trained or fine-tuned model requires recorded data provenance, split definitions, random seeds, package/model versions, parameters, raw outputs, and held-out evaluation.

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

Current scope is a Python software prototype and simulation. The formal research question, formal scientific contribution, and final hypotheses are not yet specified in the repository. Do not invent them.

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

Planned modules are not yet implemented. When implementing, keep module names and boundaries traceable to the roadmap unless new project documents supersede it.

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

No repository configuration currently pins these dependencies. Do not invent install, test, lint, format, or run commands. Inspect actual config files first if they are added later.

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

Planned datasets include self-recorded WAV commands with transcripts, custom CSV or GeoJSON mission locations, and public imagery datasets such as VisDrone, UAVDT, DOTA, xView, and Agriculture-Vision. No dataset is currently present. When adding data, record source, license/access notes, preprocessing steps, and train/test/evaluation splits in documentation.

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
- Currently unspecified: formal research question, formal contribution, exact architecture diagram, exact package versions, dataset licenses, experiment protocol details, baselines, acceptance thresholds, CI, tests, and deployment process.

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
