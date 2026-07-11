# Roadmap Retrospective Audit

Date: 2026-07-08

Update: 2026-07-09

The corrective Week 2 benchmark has now been completed and the downstream
synthetic gates for Weeks 3, 4, and 5 have been rerun. The current decision is
that Week 6 may begin, but only under the roadmap's computer-vision scope and
with the same research-integrity limits used for the earlier weeks.

Current rerun status:

- Week 2 completion gate: passed with no blockers using the fresh 30-record
  post-development audio benchmark.
- Week 3 completion gate: passed with no blockers under the synthetic custom-map
  grounding scope.
- Week 4 completion gate: passed with no blockers for high-level mission-plan
  generation, not execution.
- Week 5 completion gate: passed with no blockers for deterministic scheduling
  baselines, not route optimization or safety validation.

Important Week 2 update:

- Fresh Whisper ASR evaluation over 30 post-development recordings recorded
  exact transcript accuracy `0.80` and mean WER `0.0485`.
- Fresh intent evaluation over human-reviewed audio intent labels recorded
  `deterministic_v3` exact intent accuracy `0.60` on human transcripts and
  `0.5667` on Whisper transcripts.
- `trained_nb_human_curated_v2` matched the same exact and field accuracies on
  this fresh benchmark because its rule overrides make it follow the same
  bounded extraction path for these commands.
- The transformer span-to-intent path remains a documented negative-result path;
  no fresh transformer score is claimed for the post-development manifest.

These updates do not mean the language front end is solved. They mean Week 2 now
has a cleaner frozen benchmark and explicit caveats, so Weeks 3-5 can be treated
as valid synthetic module slices again.

Purpose: check whether Shepherd-AI has actually completed each roadmap week in enough depth for a serious research project, rather than advancing because a minimal demo exists.

Sources checked:

- `AGENTS.md`
- `docs/roadmap.pdf`
- `docs/literature_to_implementation.md`
- `docs/implementation_plan.md`
- `docs/project_synthesis.md`
- Literature-review export Markdown inventory under `docs/literature_review/ExportBlock-44375080-06b3-45d5-a3ed-ac880ba80cd6-Part-1.zip`
- Existing Week 2 status, risk, and handoff reports
- Existing Week 3, Week 4, and Week 5 completion audits
- Current notebooks, source modules, datasets, outputs, and reports

## Executive Decision

Do not start Week 6 yet.

The earliest technically significant incomplete milestone is Week 2: speech recognition and intent extraction. Week 2 has real work, including Colab/T4 transformer training for span extraction, local Whisper ASR evaluation, labeled command data, and multiple evaluations. However, its own reports state that the current handoff is provisional, post-hoc, and not a clean final benchmark. The trained transformer span path is still weak for final intent JSON on the 30-record audio transcript benchmark.

Weeks 3-5 have useful deterministic simulation slices, but they depend on the provisional Week 2 intent interface. They should be treated as downstream development modules, not proof that the language front end is solved.

## Week 1: Environment Setup And Repository Exploration

Roadmap tasks:

- Create a Google Drive folder.
- Open a new notebook.
- Clone the repository.
- Explore repository structure and README.
- Install required Python packages.
- Document architecture with a simple flow diagram.
- Create a GitHub repository for extensions.

Evidence present:

- Repository exists and is under Git/GitHub.
- `README.md`, `pyproject.toml`, package structure, tests, dataset/output/report directories, and notebooks exist.
- `docs/project_synthesis.md` and `docs/implementation_plan.md` document the project and roadmap-derived milestones.
- `notebooks/Notebook1_Setup.ipynb` exists but is thin.

Gaps:

- No rich Week 1 project journal artifact exists.
- Notebook 1 does not yet install or verify the full planned stack.
- No dedicated architecture flow diagram artifact for the whole system is present; Week 4 has a mission-flow diagram, but that is not a full project architecture sketch.

Status: partially complete. This is a documentation/setup gap, not the main technical blocker.

## Week 2: Speech Recognition And Intent Extraction

Roadmap tasks:

- Create NLP notebook.
- Accept typed commands and uploaded audio.
- Convert speech to text using Whisper.
- Extract action, number of drones, location, target, and constraints.
- Store results in JSON.
- Create WAV command dataset with transcripts.
- Deliver speech-to-text pipeline, intent parser, and example command dataset.

Evidence present:

- `notebooks/Notebook2_NLP.ipynb` and `notebooks/Notebook2_NLP_Colab_T4.ipynb`.
- Deterministic intent parser and trainable intent/span baselines.
- Human-written command dataset and human-verified span dataset.
- Whisper ASR script and local-GPU ASR outputs.
- Colab/T4 DistilBERT token-classifier training metadata and metrics.
- Transcript/intent evaluations and error analysis.
- Week 2 status report, risk audit, and Week 2 to Week 3 handoff.

Key metrics currently recorded:

- 10-record local audio ASR: exact transcript accuracy 0.90 and mean WER 0.01.
- 30-record audio generalization ASR: exact transcript accuracy 0.60 and mean WER about 0.0716.
- Expanded 85-record Colab/T4 DistilBERT span model: test entity F1 about 0.7857.
- Span-to-intent assembly on the 10-record held-out span test split: exact intent accuracy 0.50.
- On the 30-record `audio_v2_holdout` transcript benchmark, transformer span paths are weak for final JSON:
  - Human transcripts: raw span assembly 0.1667 exact, hybrid span parser 0.20 exact, deterministic parser 1.00 exact.
  - ASR transcripts: raw span assembly 0.1333 exact, hybrid span parser 0.1667 exact, deterministic parser 0.90 exact.

Gaps:

- No clean post-`deterministic_v3` final held-out command/audio benchmark.
- The strongest handoff path is still `deterministic_v3`, which was developed after inspecting holdout errors.
- Transformer span extraction is trained, but the trained span-to-intent path is not reliable enough to be the primary mission-intent interface.
- Current audio evidence is small, partly retrospective, and local-GPU for Whisper rather than Colab/T4.
- Audio-linked intent labels are derived from matching text command records rather than a separately adjudicated audio-intent benchmark.
- No spaCy fine-tuning result exists.

Status: not research-complete. Week 2 should be revisited before starting Week 6.

Corrective goal:

- Build a fresh, non-overlapping Week 2 evaluation packet after the current parser/model state.
- Human-verify intent labels and, where needed, spans.
- Evaluate deterministic, trained NB, transformer span assembly, and hybrid span parser on the same frozen benchmark.
- Decide the provisional primary intent interface from clean evidence, not same-batch development.
- Preserve negative transformer results instead of hiding them.

## Week 3: Command Grounding And Map Representation

Roadmap tasks:

- Build a simple virtual map.
- Create CSV regions and coordinates.
- Map terms such as north or greenhouse to coordinates.
- Display locations with Folium.
- Test grounding using multiple commands.
- Deliver map dataset, grounding module, and interactive map visualization.

Evidence present:

- CSV and GeoJSON map artifacts.
- Grounding module, dataset validation, ambiguity handling, clarification artifacts, map visualization, map coverage audit.
- Human-written grounding benchmark over the custom synthetic map.
- Week 3 completion audit with no blockers under the synthetic-map scope.

Gaps:

- No real-world map benchmark.
- No semantic-map/retrieval comparison.
- Human benchmark is over the custom synthetic map, not public or real map data.
- Polygon support is basic; route/safety geometry is deferred.

Status: complete enough as a synthetic simulation slice, but not real-world grounding evidence.

## Week 4: Mission Planning

Roadmap tasks:

- Convert high-level requests into task sequences.
- For a scan command: take off, fly to destination, capture images, run vision model, save results, return.
- Represent tasks using lists or graphs.
- Deliver planner notebook, decomposition examples, and mission-flow diagrams.

Evidence present:

- Mission-planning module and CLI.
- NetworkX-backed task/dependency graph.
- Scan sequence includes capture images and downstream vision-model step.
- Planning examples, focused planning cases, mission-flow diagram, and completion audit.

Gaps:

- This is not route optimization.
- This is not safety validation.
- This is not simulation execution.
- Vision is represented as a planned downstream step only, not actual inference.

Status: complete enough for the Week 4 roadmap slice, with correct deferrals.

## Week 5: Multi-Drone Coordination

Roadmap tasks:

- Simulate three drones.
- Automatically assign missions.
- Display assignments in tables.
- Implement simple scheduling logic.
- Compare assignment strategies.
- Deliver scheduler notebook, allocation visualization, and example simulations.

Evidence present:

- Simulated three-drone fleet.
- Scheduling module and CLI.
- Strategies: `round_robin`, `least_loaded`, `nearest_available`.
- Assignment table, strategy comparison JSON, HTML allocation visualization, and completion audit.
- Default run assigns 6 / 6 tasks across all three drones.

Gaps:

- This is not route optimization.
- This is not safety validation.
- This is not real execution.
- Strategies are simple baselines, not Hungarian, auction, CBBA, or learned allocation.
- No dynamic task-arrival, failure, or robustness experiments yet.

Status: complete enough for the Week 5 roadmap slice, but not a full task-allocation research study.

## Corrective Order

1. Pause Week 6.
2. Return to Week 2 and create a clean post-development benchmark.
3. Add a Week 2 completion gate comparable to Weeks 3-5.
4. Re-run Week 3-5 through the selected Week 2 interface only after Week 2 has a cleaner handoff.
5. Only then begin Week 6 vision integration.

## Why Week 2 Comes First

The entire Shepherd-AI pipeline starts with speech/text to intent. If the intent interface is provisional or post-hoc, then grounding, planning, and scheduling can only be interpreted as module-level development checks. A serious research project needs the language front end to have clearly separated data splits, human-reviewed labels, negative results, model provenance, and a frozen evaluation before later end-to-end claims.
