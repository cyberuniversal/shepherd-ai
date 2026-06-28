# Shepherd-AI Project Synthesis

## Source Scope

This synthesis is based only on the current repository documents read on 2026-06-28:

- Root `AGENTS.md`
- `docs/roadmap.pdf`
- `docs/literature_review/ExportBlock-44375080-06b3-45d5-a3ed-ac880ba80cd6-Part-1.zip`
- Every Markdown file inside the literature-review export

The user-requested `docs/roadmap/` directory does not exist in the repository. The available roadmap source is `docs/roadmap.pdf`.

## What Shepherd-AI Is

Shepherd-AI is planned as a Python research prototype for "Natural Language Multi-Drone Mission Planning and Coordination." The roadmap describes a software simulation in which an operator issues voice or text commands such as sending two drones north to scan crops while another drone checks an irrigation canal. The system is intended to convert those commands into structured mission intents, grounded map locations, executable task plans, multi-drone assignments, safety-checked simulated actions, image-analysis outputs, and mission reports.

The roadmap explicitly states that no physical drone hardware is required. Physical-drone papers in the literature review are background evidence and design guidance, not implementation requirements for this repository.

## Problem It Is Intended To Solve

The roadmap problem is supervisory mission control: a non-specialist operator should express a multi-drone inspection mission in natural language instead of manually writing low-level drone instructions. The planned software must bridge vague language, map locations, task decomposition, virtual drone allocation, computer-vision analysis, safety validation, feedback, and evaluation.

The literature review reinforces that this is not just a language-to-command problem. Similar systems struggle when an LLM is allowed to control execution directly, when generated outputs are unstructured, when maps and world state are assumed correct, or when evaluation checks only format validity rather than task success.

## Intended Pipeline

The roadmap proposes this complete pipeline:

1. Accept typed or spoken mission commands.
2. Use Whisper to convert speech to text for audio commands.
3. Extract structured mission intent as JSON fields such as action, drone count, location, target, and constraints.
4. Ground human terms such as `north`, `greenhouse`, or `irrigation canal` into coordinates from a custom map dataset.
5. Generate mission steps such as takeoff, fly to destination, capture images, run vision, save results, and return.
6. Allocate and schedule tasks across simulated drones, initially using simple scheduling logic and strategy comparison.
7. Run computer-vision inference on aerial imagery, planned around Ultralytics YOLO.
8. Validate safety constraints including battery threshold, restricted areas, altitude limits, and drone availability.
9. Provide clarification dialogue, simulated status updates, and mission feedback.
10. Integrate the modules into an end-to-end demo and evaluate intent extraction, grounding, scheduling quality, detection performance, and overall execution time.
11. Produce reports, figures, documentation, and a research-paper draft/final version.

## Major Planned Components

- Speech and text input interface.
- Speech-to-text component using Whisper.
- Intent extraction component that emits bounded JSON.
- Command grounding component backed by a custom CSV or GeoJSON map.
- Mission planner that decomposes high-level requests into task sequences or graphs.
- Multi-drone scheduler/allocation component.
- Vision component using Ultralytics YOLO on public aerial imagery datasets.
- Safety validator for battery, restricted areas, altitude, and availability.
- Feedback/reporting component.
- Evaluation notebooks or scripts.
- Research documentation and paper artifacts.

## Literature Findings That Influence The Design

The literature review repeatedly supports a hierarchical architecture: language models should interpret goals, translate commands, or propose structured plans, while deterministic software validates syntax, checks safety, performs scheduling, and controls execution.

TACOS shows the value of separating a high-level coordinator from an execution supervisor, preserving unfinished work, and preventing LLMs from directly handling low-level trajectory generation. Swarm-Steward similarly uses plan-then-execute orchestration, live state summaries, tool boundaries, and map retrieval for large swarm commands. CommandSwarm demonstrates the usefulness of behavior trees, whitelisted primitives, command-level safety filtering, and deterministic parser validation.

The PDDL-goal translation paper supports using LLMs or parsers to translate natural language into formal goals rather than asking the model to solve the entire planning problem. PROGPROMPT shows that executable-looking plans can still fail to achieve task goals, so Shepherd-AI should distinguish format validity from mission success.

VLMaps and GeoText-1652 are relevant to grounding language in maps or aerial imagery, but neither makes Shepherd-AI's grounding module solved. VLMaps is mainly a semantic navigation and mapping system; GeoText-1652 is a retrieval/grounding benchmark, not a complete drone-control system.

The task-allocation review supports evaluating assignment strategies under shared metrics, but its own tables conflict with some narrative claims about which algorithm is best. Shepherd-AI should preserve that caveat and avoid treating one assignment algorithm as universally superior.

The aerial-ground papers show that language-specified missions benefit from semantic maps, perception, and closed-loop monitoring, but those results often involve physical robots, controlled testbeds, known waypoints, or small trial counts. Simulation and physical results should not be treated as interchangeable.

## What Similar Systems Have Accomplished

Similar systems in the literature have demonstrated:

- Natural-language multi-UAV coordination with structured APIs and closed-loop supervision.
- Large-swarm natural-language orchestration with live state summaries, tool calls, and map references.
- Web-of-Things/MCP-style access to drone telemetry and actions in simulation.
- Bilingual or multilingual speech/text front ends for drone commands.
- Language-to-PDDL goal translation for classical planning.
- Language-to-behavior-tree generation with parser validation.
- Open-vocabulary semantic maps for language-referenced navigation.
- Aerial image/text retrieval benchmarks for natural-language geolocalization.
- Comparative simulation frameworks for multi-UAV task allocation.
- Aerial-ground cooperation where a UAV helps a ground robot with semantic mapping.

These are established by the reviewed papers, not by this repository's implementation.

## Limitations And Gaps

The repository does not yet contain a working prototype, source modules, notebooks, datasets, experiments, tests, or package configuration beyond the files added for the first milestone. The formal research question, formal contribution, exact architecture diagram, package versions, dataset licenses, experiment protocol, baselines, thresholds, and CI process are not stated in the current source documents.

The literature review identifies several general limitations in related systems: limited real-world validation, reliance on known maps or noiseless state, weak semantic validation, small or synthetic datasets, ambiguity in natural-language grounding, failure to distinguish valid output from task success, and incomplete evaluation of safety classifiers or runtime monitors.

## Intended Investigation Or Contribution

The roadmap supports an intended investigation into whether the planned modules can be integrated into a software-simulation prototype that turns voice or typed mission commands into planned, allocated, safety-checked, vision-supported multi-drone missions with evaluation results.

The repository documents do not yet state a finalized research question, formal novelty claim, or hypothesis. The safe current framing is:

- Fact: Shepherd-AI is planned as a Python software simulation, not a physical-drone deployment.
- Fact: The roadmap defines modules for speech, intent extraction, grounding, planning, scheduling, vision, safety, feedback, integration, evaluation, and paper writing.
- Fact: The literature supports bounded, inspectable representations and deterministic validation.
- Untested hypothesis: these planned modules can be integrated into a working end-to-end prototype with useful evaluation results.
- Not stated: the final scientific contribution or acceptance thresholds.

## Established Claims Versus Hypotheses

Established by repository documents:

- The roadmap's intended stack includes Python, Whisper, Hugging Face Transformers, spaCy, Ultralytics YOLO, NetworkX, Matplotlib, Folium, Pandas, and NumPy.
- The roadmap's intended data areas include commands, sample audio, maps, aerial images, outputs, reports, source code, and notebooks.
- The roadmap's intended evaluation metrics are intent extraction accuracy, grounding accuracy, scheduling quality, detection performance, and overall execution time.
- The literature review supports hierarchical language-to-structured-plan designs, deterministic validation, conventional planners/controllers, and closed-loop monitoring.

Still hypotheses or not implemented:

- That Shepherd-AI can achieve reliable end-to-end mission execution.
- That the first intent parser will generalize beyond the roadmap examples.
- That any public aerial dataset has been downloaded, licensed, or preprocessed.
- That Whisper, spaCy, Transformers, YOLO, NetworkX, Folium, or any other planned dependency is installed or configured.
- That any safety guarantee has been established.
- That the final research contribution or novelty claim has been proven.
