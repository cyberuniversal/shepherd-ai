# Shepherd-AI: Evidence-Gated Natural-Language Mission Planning for Simulated Multi-Drone Inspection

**Week 9 first draft. Not a final paper or accepted novelty claim.**

## Abstract

Natural-language interfaces can reduce the effort required to specify
multi-drone missions, but language-model output is not a reliable substitute
for state-aware planning, allocation, safety validation, or flight control.
Shepherd-AI is a Python research prototype that converts spoken or typed
commands into bounded mission-intent records, grounds them to a custom
simulation map, creates dependency-aware task sequences, allocates work among
simulated drones, applies deterministic safety checks, executes deterministic
software telemetry, and analyzes registered aerial imagery. The architecture
uses learned models for speech recognition, intent extraction, and vision while
keeping mission representations serializable and execution gates inspectable.
A fixed roadmap scenario was evaluated with one human-recorded command, a
frozen Whisper base model, a frozen DistilBERT token-classification checkpoint,
a three-drone software simulation, and a frozen Agriculture-Vision
segmentation checkpoint. The run recorded word error rate 0.07143, intent exact
match 1/2, grounding accuracy 2/2, scheduling completion 3/3, mission-class
modified mean intersection-over-union 0.02356 over 59 images, and 31.3343
seconds of measured warm-model execution time. The low vision score is retained
as evidence that successful orchestration does not imply reliable perception.
In a separate 38-case evidence-decision diagnostic, the modular pipeline made
38/38 registered `proceed`, `clarify`, or `block` decisions, with 0/26 false
refusals and 0/12 silent-misexecution proxy errors. A command-only
no-evidence-gate ablation made 12/12 such errors. Clarification recovery
succeeded in 3/3 registered valid attempts. Most non-grounding cases are synthetic
development diagnostics, and the ablation is not a monolithic LLM. The
evidence therefore supports a candidate contribution in explicit,
operator-facing evidence gating and failure-mode measurement, not physical
safety, broad generalization, or a claim of being the first such system.

**Keywords:** natural-language robotics, multi-drone coordination, mission
planning, task allocation, semantic grounding, computer vision, software
simulation

## 1. Introduction

Operating several unmanned aerial vehicles through rigid interfaces requires
the operator to translate a mission objective into device-specific actions.
Natural language offers a more direct way to express goals such as inspecting
crops in one region while assigning another drone to irrigation. The language
interface, however, introduces uncertainty at the point where ambiguous words,
incorrect transcriptions, unsupported actions, stale state, or missing map
references can affect execution.

The reviewed literature repeatedly separates semantic interpretation from
robot execution. TACOS uses coordinator and supervisor roles while delegating
trajectory generation and collision avoidance to conventional software [L1].
Swarm-Steward and the Web-of-Drones work similarly emphasize typed tools,
current state, and monitored execution [L2, L3]. PDDL-goal translation and
behavior-tree generation show that language models can produce constrained
intermediate representations, but those representations still require parsers
and semantic checks [L7, L8]. These findings motivate Shepherd-AI as a bounded,
inspectable pipeline rather than an unrestricted language-model controller.

Shepherd-AI investigates whether the roadmap's voice-to-report pipeline can be
assembled reproducibly in software simulation while preserving module-level
evidence and failure states. Its candidate contribution is an evidence-gated
decision policy: locally valid language or planning output is insufficient to
advance when map references are ambiguous, grounded references conflict,
required state is missing, or configured safety checks fail. The paper measures
false refusals, silent misexecution, clarification recall, and clarification
recovery rather than treating format-valid plans as success. The project
currently demonstrates one fixed end-to-end scenario and a controlled
decision diagnostic. It does not show generalization to open environments or
physical drones.

## 2. Motivation

Prior systems have demonstrated meaningful pieces of language-guided robotics.
TACOS coordinates multiple UAVs, preserves unfinished work, and replans after
failures [L1]. VLMaps links open-vocabulary language to spatial maps [L9].
GeoText-1652 supplies a large aerial image-text retrieval benchmark with
spatial annotations [L10]. CommandSwarm improves constrained behavior-tree
generation through adaptation and deterministic parsing [L8]. Hierarchical
aerial-ground systems combine language interpretation, semantic maps, and
conventional planners [L15].

These systems also expose limitations relevant to Shepherd-AI. High syntactic
validity does not guarantee mission success [L4, L8, L13]. Known maps and
globally available targets can hide the difficulty of perception [L1]. Code
generation can create verification and execution risks [L9, L13, L14]. Learned
vision-language grounding remains imperfect, and retrieval benchmarks are not
equivalent to closed-loop navigation [L9, L10]. Allocation studies do not
support one universally superior strategy; the repository review of [L12] also
records conflicts between some narrative claims and extracted tables.

The practical motivation is therefore not to replace every robotics component
with one model. It is to keep language handling, planning, allocation,
perception, safety, execution, and evaluation separate enough that errors can
be measured and blocked at their actual boundary. The research question for
the present revision is: **does explicit evidence gating reduce silent
advancement on ambiguous, conflicting, or policy-invalid missions without
unnecessarily refusing registered valid missions?**

## 3. Problem Statement

Given a spoken or typed operator command, a registered map, a simulated drone
fleet, configured safety policy, and registered aerial imagery, the system must:

1. transcribe speech when audio is supplied;
2. produce a bounded mission intent containing action, drone count, location,
   target, and constraints;
3. resolve language references to known map records or request clarification;
4. produce an inspectable task graph;
5. allocate task replicas to available simulated drones;
6. reject unresolved or policy-violating missions before execution;
7. emit deterministic mission telemetry and status feedback; and
8. bind relevant imagery to mission clauses, run frozen vision inference, and
   create traceable reports.

The current scope is a Python software simulation. Collision-free physical
trajectory control, onboard localization, communication failure, outdoor
deployment, and safety certification are outside the demonstrated scope.

## 4. Objectives

The project objectives, derived from the roadmap, are:

- support speech and typed command input;
- compare deterministic and trained intent-extraction paths;
- ground location language to coordinates without inventing unknown places;
- create dependency-aware mission steps and serializable graphs;
- compare simple deterministic multi-drone scheduling strategies;
- train and evaluate aerial-image vision baselines using documented splits;
- enforce configured battery, altitude, availability, restricted-area, route,
  and separation checks outside learned models;
- support clarification, operator lifecycle controls, telemetry monitoring, and
  unfinished-work preservation;
- run the fixed end-to-end software scenario; and
- preserve raw outputs, model metadata, seeds, splits, failures, and derived
  metrics for paper preparation.

The candidate contribution evaluated in this draft is the combination of:

1. a separately testable voice-to-perception multi-drone inspection pipeline;
2. explicit `proceed`, `clarify`, and `block` decisions at grounding and safety
   boundaries; and
3. failure-mode metrics for false refusal, silent misexecution, and
   clarification recovery.

This is not a claim that modular robotics, safety validation, perception, or
clarification is individually novel.

## 5. Related Work

### 5.1 Hierarchical Language-Guided Coordination

TACOS demonstrates centralized one-to-many coordination using a semantic
Coordinator and an execution-monitoring Supervisor, with conventional software
handling trajectories [L1]. Its monolithic ablation performed substantially
worse than the two-role hierarchy on its multi-stage inspection task. TACOS
assumes a complete, accurate world state and does not use onboard perception
to discover its simulated targets [L1]. Shepherd-AI differs by separating
speech, intent extraction, map grounding, planning, classical scheduling,
perception, and safety into individually testable modules. This modularity is
an engineering distinction, not by itself a novelty claim.

RoCo assigns an LLM agent to each robot for dialogue, subtask planning, and
waypoint proposals, then uses centralized motion planning and environment
feedback [E1]. RoCo also uses OWL-ViT in real-world experiments; its authors
identify perception errors as a major failure source and evaluate oracle human
correction. It is therefore inaccurate to claim that all close systems lack
perception. Swarm-GPT combines LLM-generated drone choreography with a
model-based trajectory planner and safety layer, but it addresses synchronized
performance design rather than semantic inspection and target discovery [E2].
LLaMAR uses a plan-act-correct-verify architecture for partially observable
multi-agent tasks [E3], so complete-world assumptions likewise cannot be
attributed to all related systems.

Swarm-Steward uses plan-then-execute separation,
retrieval of map and state information, deterministic tools, and operator
preview, and its reviewed design can issue clarification requests [L2]. The
Web-of-Drones study exposes typed robot capabilities and live state through
agent-enhanced interfaces [L3]. The hierarchical aerial-ground system combines
high-level language models with a visual-language semantic map and conventional
planners [L15]. The remaining question is not whether prior work ever validates
or clarifies. It is whether an integrated multi-UAV inspection pipeline
explicitly measures insufficient/conflicting-evidence decisions, false
refusals, silent misexecution, and recovery under a shared protocol.

### 5.2 Structured Plans And Executable Programs

Natural-language-to-PDDL work reports that translating desired goals can be
more reliable than asking a model to generate complete plans, leaving search
to a classical planner [L7]. CommandSwarm constrains generation to whitelisted
behavior-tree nodes and rejects malformed XML [L8]. PROGPROMPT and GenSwarm
show the flexibility of generated robot programs and code policies [L13, L14],
but arbitrary generated code adds an execution boundary that must be secured.
Shepherd-AI therefore uses JSON-compatible data classes and fixed Python APIs;
it does not execute model-generated Python.

### 5.3 Grounding, Mapping, And Perception

VLMaps projects vision-language embeddings into a persistent map that supports
open-vocabulary spatial queries [L9]. GeoText-1652 evaluates text-to-aerial-
image retrieval and region-level spatial correspondence, but does not itself
perform drone control [L10]. Air-ground collaboration and hierarchical
aerial-ground work address semantic mapping in unknown environments [L6, L15].
Shepherd-AI's current grounding is narrower: aliases and directional terms are
resolved against a custom synthetic CSV/GeoJSON map. Learned open-vocabulary
map grounding is not implemented.

### 5.4 Voice Interfaces, Simulation, And Allocation

Dialogue-based PX4 work and real-time UAV-control work demonstrate speech or
language interfaces but also show that formatting and command generation must
be distinguished from full mission success [L4, L5]. SkySim provides a ROS2
simulation path for natural-language swarm formations and waypoint generation
[L11]. The task-allocation comparison examines centralized and distributed
methods under shared metrics [L12]. Shepherd-AI implements simpler
round-robin, least-loaded, and nearest-available baselines and reports only
their behavior on registered synthetic cases; it does not claim global
optimality.

## 6. Proposed Method

Figure source `reports/figures/week9_system_architecture.mmd` describes the
active architecture. The pipeline is hierarchical in responsibility even
though it is implemented as a modular Python prototype.

| Stage | Implemented role | Execution boundary |
|---|---|---|
| Input and ASR | Accept typed text or transcribe registered WAV audio with Whisper | ASR output remains separate from intent scoring |
| Intent extraction | Produce action, count, location, target, and constraints | Bounded schema; deterministic and trained paths remain distinguishable |
| Grounding | Resolve aliases and directions to map IDs and coordinates | Ambiguous or unknown references require clarification |
| Planning | Build ordered mission steps and a dependency graph | No route optimization or low-level control |
| Scheduling | Replicate multi-drone work and compare deterministic allocators | No claim of global optimality |
| Safety and dialogue | Apply configured policy and route checks; collect resolutions | Learned output cannot bypass deterministic rejection |
| Simulation and supervision | Emit deterministic state transitions and telemetry | Software simulation only |
| Vision | Run registered frozen models on mission-bound imagery | Dataset role and class mapping remain explicit |
| Reporting | Derive metrics, logs, figures, and completion gates | Raw evidence is preserved separately from analysis |

The system passes serializable records between modules. Original command text,
parser identity, map IDs, coordinates, plan steps, assignments, policy outcomes,
telemetry events, model hashes, and output paths remain inspectable. This
design follows the literature's recurring recommendation that language models
propose semantic structures while deterministic software validates and
executes known operations [L1-L3, L7, L8, L15].

## 7. System Architecture

The input layer accepts typed commands directly or a Whisper transcript. The
intent layer creates one record per command clause. Grounding searches the
registered map and returns grounded, ambiguous, or unresolved status. A
clarification response can resolve an ambiguous clause without rewriting the
original command. The planner converts grounded intents into steps such as
constraint review, takeoff, travel, image capture, vision processing, result
storage, and return. NetworkX represents step dependencies.

The scheduler assigns task replicas to a three-drone simulated fleet using a
selected deterministic strategy. The safety layer evaluates availability,
battery, altitude, restricted-area intersection, route clearance, and
inter-drone separation using configured synthetic thresholds. Only approved
missions enter the deterministic simulator. Supervision records operator and
telemetry events, including pause, resume, cancellation, completion, and
runtime intervention. Vision inference is not allowed to use arbitrary prior
development images: mission image records explicitly bind a clause and map
location to registered images. Reports are derived from raw stage outputs.

The current architecture does not provide a feedback controller, physical
flight stack, SLAM, collision-avoidance trajectory optimizer, or online target
discovery. The Folium output visualizes deterministic telemetry; it is not a
physics engine.

## 8. Methodology

### 8.1 Data And Provenance

The NLP work includes human-written command records, human-verified span labels,
and human-recorded WAV files. Model-generated text is not relabeled as
human-written merely because it is reviewed. The expanded token-classification
export contains 85 records split into 57 training, 18 validation, and 10 test
records. A separate 30-record post-development benchmark supports the Week 2
handoff; its size limits generalization claims.

Grounding uses a custom synthetic map with 20 main records, including obstacle
and restricted-area roles, plus a 22-record human-written grounding benchmark.
Planning evaluates those 22 records and seven focused planning cases.
Scheduling uses a three-drone synthetic fleet. Week 7 uses registered synthetic
preflight, clarification, route, supervision, integration, and policy-
sensitivity cases.

Vision follows two distinct tasks. VisDrone2019-DET supports object detection
with its official 6,471-image training and 548-image validation splits;
test-dev is not used for model selection. Agriculture-Vision 2017 miniscale
supports semantic segmentation. Its principal development protocol uses
seed 17, 256 training tiles, 256 validation tiles, a small U-Net, and BCE-Dice
loss. Licensed pixels and checkpoints remain in private storage; committed
summaries record hashes, parameters, package versions, split roles, and
metrics.

### 8.2 Training And Model Selection

The trained intent path is a DistilBERT token classifier fine-tuned on the
human-verified BIO span dataset in Colab on a Tesla T4. Deterministic parsers
remain baselines and integration fallbacks rather than being mislabeled as
trained models. Whisper base is frozen for speech transcription.

The Agriculture-Vision small U-Net is trained from scratch under the fixed
seed-17 protocol. The registered development comparison selected BCE-Dice
within the declared validation workflow; the resulting checkpoint is frozen
for Week 8. The VisDrone YOLOv8n detector is initialized from published
weights, fine-tuned for 50 epochs on the official training split, and selected
on the official validation split. These are separate segmentation and
detection experiments and their metrics are not interchangeable. The fixed
agricultural Week 8 scenario uses the U-Net result, not the YOLOv8n detector;
the existence of a trained detector must not be used to obscure the scenario's
low segmentation performance. On the official VisDrone validation split, the
frozen YOLOv8n run recorded precision 0.43116, recall 0.32034, mAP50 0.29677,
and mAP50-95 0.16724 after 50 training epochs. Those detection values are
Week 6 model evidence, not agricultural mission success.

### 8.3 Fixed End-To-End Scenario

The roadmap command is: "Send two drones north to inspect crops and one drone
east to inspect irrigation." One human recording of that exact scenario is
registered by SHA-256. The command is decomposed into two clauses and three
requested drones. Because the custom map does not silently equate a directional
phrase with an irrigation landmark, the operator resolution binds the second
clause to East Field. The resolved schedule drives 43 deterministic telemetry
records. Mission imagery comes from a disjoint remainder of the official
Agriculture-Vision validation split, excluding 768 development IDs. Selection
uses a seeded hash with seed 29 and yields 59 labeled images.

Crop inspection is evaluated against non-water agricultural anomaly classes;
irrigation inspection is evaluated against water and waterway. This is a
declared Shepherd-AI task-to-label mapping, not a claim made by the dataset
authors. Classes absent from the relevant labeled evidence remain null rather
than being converted to zero.

### 8.4 Metrics And Traceability

The roadmap requires intent extraction accuracy, grounding accuracy,
scheduling quality, detection performance, and overall execution time. The
generated table `outputs/tables/week9_end_to_end_metrics.csv` is the numeric
source for this draft.

| Metric | Value | Denominator | Interpretation |
|---|---:|---:|---|
| Intent extraction accuracy | 0.50000 | 2 clauses | Exact structured-intent match |
| Grounding accuracy | 1.00000 | 2 clauses | Resolved destination match |
| Scheduling quality | 1.00000 | 3 replicas | Assigned requested replicas / total replicas |
| Detection performance | 0.02356 | 6 evaluated classes, 59 images | Mission-class modified mean IoU |
| Overall execution time | 31.3343 s | 1 run | Sum of measured warm-model stage times |

Whisper WER is reported separately as 0.07143 on one exact-scenario recording.
Intent field accuracy is 9/10 even though exact clause accuracy is 1/2. The
vision result includes crop-clause mean IoU 0.02827 and irrigation-clause mean
IoU 0.0. Only drydown has nonzero class IoU in the crop clause. This negative
result prevents the completion of mission orchestration from being interpreted
as successful visual understanding.

The measured runtime excludes model loading and notebook orchestration. Vision
inference accounts for 28.3455 seconds, ASR for 2.7087 seconds, intent inference
for 0.2537 seconds, preparation for 0.0106 seconds, and simulation for 0.0157
seconds. `reports/figures/week9_stage_runtime.png` visualizes this breakdown.

### 8.5 Reproducibility And Claim Limits

Every Week 8 paper metric traces to a promoted JSON artifact and denominator.
The Week 9 builder validates the completion audit, source paths, finite metric
values, positive denominators, and claim-limit flags before generating tables
or figures. Raw predictions remain separate from derived summaries. Private
pixels, audio, and model weights are not committed, but registered hashes and
metadata support identity checks.

The evidence supports completion of the bounded roadmap scenario in software
simulation. It does not support claims of physical-drone control, real-world
safety, open-world perception, statistically reliable end-to-end performance,
or state-of-the-art performance.

### 8.6 Evidence-Aware Decision Diagnostic

The versioned protocol in `docs/week9_evidence_aware_protocol.md` combines four
registered strata:

- 22 existing human-written grounding commands;
- 12 existing synthetic preflight cases;
- 4 synthetic conflicting-reference controls; and
- 4 existing synthetic clarification dialogues.

The 38 decision cases use gold labels `proceed`, `clarify`, or `block`.
`proceed` means advance to the next bounded stage, not mission success. The
comparison baseline sees only command text and proceeds whenever the existing
parser identifies an action. It intentionally removes map, fleet, policy, and
intermediate evidence. It is a mechanism ablation, not TACOS and not a
monolithic LLM.

## 9. Results

### 9.1 Fixed End-To-End Scenario

The fixed scenario completed the bounded software orchestration, but the
results are mixed. Whisper WER was 0.07143 on one recording. Intent exact match
was 1/2 clauses despite 9/10 field matches. Grounding and scheduling were 2/2
and 3/3 respectively. Mission-class modified mean IoU was 0.02356 over 59
images, including 0.0 for the irrigation clause. These values remain the
primary end-to-end result and do not support a strong perception claim.

### 9.2 Evidence Decisions

Raw per-case outputs and denominators are stored in
`outputs/evaluations/week9_evidence_aware_decisions_v1.json`.

| System | Correct decisions | False refusals | Silent-proceed proxy errors | Clarification recall | Block recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Shepherd evidence-aware pipeline | 38/38 | 0/26 | 0/12 | 6/6 | 6/6 |
| Single-pass actionability ablation | 26/38 | 0/26 | 12/12 | 0/6 | 0/6 |

The stateful dialogue and conflict-resolution paths recovered in 3/3
registered valid attempts. Dialogue terminal status matched all 4 synthetic
cases, including retry, cancellation, and timeout outcomes. The
silent-misexecution metric is a decision-level proxy: the diagnostic records an
incorrect `proceed` decision but does not execute the wrong mission.

## 10. Discussion

The diagnostic supports the mechanism-level claim that explicit evidence gates
prevented silent advancement on the registered ambiguous, conflicting, and
policy-invalid cases without refusing the registered proceed cases. It does not
establish that Shepherd-AI will retain these rates under new maps, noisy fleet
state, adversarial language, different policies, or real operators.

The comparison is deliberately weaker than the experiment needed for a final
paper claim. The actionability ablation has no world evidence, while TACOS,
RoCo, and LLaMAR receive structured state or observations. A fair monolithic
LLM baseline must receive the same command, map, fleet, policy, and observation
packet; use a frozen model and prompt; run multiple seeds or temperatures where
applicable; and store every response. Until that experiment exists, this draft
does not claim superiority over those systems.

The low Week 8 vision result remains important. Evidence gating can stop an
unsupported mission decision, but it cannot turn a weak perception model into
a reliable detector. The paper's strongest current result is therefore
decision discipline on a bounded diagnostic, not end-to-end agricultural
inspection quality.

## 11. Candidate Contribution And Next Experiment

The defensible candidate contribution is: **a reproducible, modular
multi-drone inspection pipeline that exposes insufficient or conflicting
evidence as explicit operator-facing decisions and evaluates the resulting
false-refusal, silent-misexecution, and clarification-recovery trade-off.**

This statement is a candidate contribution, not a priority claim. The next
required experiment is a same-input comparison against at least one frozen
monolithic LLM baseline on a larger held-out ambiguity and state-conflict
benchmark. The benchmark must include human-authored ambiguous and
unambiguous commands, balanced decision classes, unseen paraphrases and map
entities, and blinded label review. Improving and reevaluating agricultural
perception remains a separate requirement; the evidence-aware result must not
replace it.

## References

The organized working bibliography is `reports/week9_bibliography.md`.
Bracketed references [L1]-[L15] correspond to the repository
literature-review export. [E1]-[E3] are additional primary sources recorded in
the same bibliography for this revision.
