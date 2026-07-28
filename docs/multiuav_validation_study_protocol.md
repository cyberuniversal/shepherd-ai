# Shepherd-AI MultiUAV-Plat Validation-Placement Study

## Status And Provenance

This document records the revised paper direction supplied by the user in
`docs/source_material/code_plan_2026-07-25.docx`.

- Source DOCX SHA-256:
  `829cfa69e2a3365d0686163fbd1548e9e0c22455535a6d725cc3289a37102f63`
- Source document date: 2026-07-25
- Repository adoption date: 2026-07-28
- Status: proposed protocol, not implemented, frozen, or evaluated
- Previous paper status: preserved as historical development evidence, but
  superseded as the active paper direction

The source DOCX contains 63 non-table paragraphs, no comments, and no tracked
changes. LibreOffice was unavailable for page rendering, so the adoption check
used complete structural text extraction rather than visual render evidence.

## Research Position

The paper is a systems-and-measurement study. It does not claim that refusal,
safety checking, offline inference, modular planning, evidence gating, or
multi-UAV language-model planning is individually novel.

The proposed bounded contribution is the combined evaluation of:

1. five matched interventions derived from each authentic source task;
2. multiple validation placements under shared model and evidence conditions;
3. failure-containment attribution;
4. joint safety, utility, latency, memory, token, model-call, and GPU-board
   energy reporting; and
5. reproducible local inference with immutable source and model revisions.

The proposed research question is:

> How does the placement of evidence validation within a local multi-UAV
> planning pipeline change where failures are contained, and what safety,
> utility, latency, memory, token, model-call, and GPU-board energy trade-offs
> result?

This remains a proposed question until the unresolved design decisions below
are registered.

## Relationship To The Roadmap And Literature

This study refines the roadmap's Week 9 and Week 10 evaluation and paper work.
It does not create an additional roadmap week or replace the implemented
software-simulation modules.

The design follows the repository literature in these ways:

- LLMs remain high-level interpreters and planners, not low-level controllers.
- Outputs use bounded API plans and strict JSON decisions.
- Deterministic validators gate execution and check schemas, identifiers,
  parameters, provenance, and safety conditions.
- Parsing, planning, validation, execution, and failure containment remain
  separately inspectable.
- Raw failures, malformed outputs, and negative results are retained.
- Evaluation separates syntactic validity, task fidelity, and actual execution.

MultiUAV-Plat was not part of the 15-paper repository literature export. It is
a newly introduced primary benchmark source and must be added to the formal
related-work record before manuscript finalization.

## Source Benchmark

Planned source:

- Repository: `https://github.com/zhangsheng93/MultiUAV-Plat`
- Required commit:
  `1794e45e421fb5de03094f0b63f9ca95f86ab42f`
- Upstream paper: *MultiUAV-Plat: An LLM-Oriented Platform, Benchmark and
  Framework for Multi-UAV Collaborative Task Planning*, arXiv:2606.31073
- Upstream-reported contents: 75 mission sessions, 1,500 natural-language
  tasks, and 9,396 validation checks

The commit resolved as upstream `main` and `HEAD` during the 2026-07-28 source
audit. The pinned `benchmark/benchmark.zip` is 11,709,646 bytes with SHA-256
`b5040097d2bfdd44600f3bf486fdb43ee3eb1247fec9c67900b5fcda6feb94a3`.
The local audit reproduced 75 sessions, 1,500 tasks, 9,396 recursively counted
validation-check leaves, and 5,794 upstream `content_aliases`. Acquisition,
license, field-boundary, and integrity details are recorded in
`docs/multiuav_source_acquisition.md` and
`datasets/multiuav_plat/source_registry_v1.json`.

The audit also found only 1,443 unique normalized canonical instructions out of
1,500. Therefore, session-level splitting alone does not establish textual
independence; exact and normalized cross-split overlap must still be measured.

## Paired Dataset Design

For every source task, the proposed dataset contains five linked variants:

1. `canonical_execute`: canonical source instruction;
2. `official_alias_execute`: source-supported alias wording;
3. `missing_information_clarify`: a minimally underspecified instruction;
4. `restored_information_execute`: the missing fact restored in matched
   wording; and
5. `resource_conflict_block`: a mission with no valid UAV-resource assignment.

The frozen leakage-control audit retains 1,473 of 1,500 source tasks. If every
retained task later yields all five valid interventions, the pre-review upper
bound is 7,365 cases. All five variants for one task form one source cluster and
must remain in the same split.

The frozen session-level split began as 60/20/20:

- training: 45 sessions and 4,500 paired cases;
- calibration: 15 sessions and 1,500 paired cases; and
- test: 15 sessions and 1,500 paired cases.

After deterministic leakage exclusions, the prospective upper bounds are
4,495 train cases, 1,450 calibration cases, and 1,420 test cases. These counts
still assume every retained source task yields all five valid interventions.
Any later exclusion removes its complete five-case cluster. Partial clusters
are invalid.

The session split is now frozen in `docs/multiuav_split_protocol.md` and
`datasets/multiuav_plat/session_split_v1.json`, using the seed
`shepherd-multiuav-split-v1`. Exact and normalized source-text overlap is
reported in that manifest. Task eligibility and official-alias selection are
frozen in `docs/multiuav_task_eligibility_protocol.md`; no five-variant cases
have been generated.

## Intervention Validity Rules

The paired design is valid only if each intervention changes the intended
evidence condition without changing unrelated mission semantics.

- A missing-information case is `CLARIFY` only when the missing fact cannot be
  recovered through the visible context or allowed observation APIs.
- A resource-conflict case is `BLOCK` only when no allowed UAV, reassignment,
  or source-supported recovery action can satisfy the mission.
- The restored-information case must differ from its missing-information pair
  only by the restored fact and unavoidable grammatical repair.
- An official alias must be traceable to source benchmark metadata or
  documentation. A manually invented paraphrase is not an official alias.
- Hidden validators, reference API sequences, and privileged state must never
  appear in model prompts.
- Automatic generation is draft construction, not final labeling. Review and
  adjudication identities must be real and pseudonymous.

## Comparison Configurations

The intended systems are:

- `M1_monolithic`: one local model call produces the decision and API plan.
- `M2_post_plan_deterministic`: the M1 plan passes through a deterministic
  post-plan safety and fidelity gate.
- `M3_stage_wise`: evidence is represented in a ledger, checked before
  planning, and validated again for plan provenance.
- `M4_post_plan_compute_matched`: a planner and a separate post-plan validator
  use the same model-call budget as M3.

All methods must receive the same visible command, mission evidence, action
schema, model family, and decoding policy. Method-specific prompts and
intermediate records must be versioned and hashed.

The exact number and purpose of model calls in M3 are not yet explicit in the
source DOCX. M3 and M4 cannot be called compute-matched until this is resolved
and tested.

## Output Contract

Every method must return strict JSON containing:

- `decision`: `EXECUTE`, `CLARIFY`, or `BLOCK`;
- `reason`;
- `clarification_question`, required only for `CLARIFY`; and
- a non-empty structured API plan for `EXECUTE`.

Malformed output is retained as `PARSE_ERROR`. It is not manually repaired,
discarded, or converted into a valid decision.

Every planned API value must be validated recursively against the visible
command and context, including:

- endpoint names;
- UAV identifiers;
- coordinates and regions;
- headings;
- distances and altitudes;
- target identifiers;
- messages and payload values; and
- ordering or dependency constraints.

The evaluator records containment as `pre_plan`, `post_plan`, `parse_error`, or
`uncontained`.

## Models And Offline Runtime

Planned local model family:

- `Qwen/Qwen2.5-3B-Instruct`
- `Qwen/Qwen2.5-7B-Instruct`

Each model must resolve to an immutable 40-character Hugging Face commit before
the locked run. The comparison is within one model family and does not support
claims about all LLMs.

Measured inference requires:

- weights cached before measurement;
- local-files-only loading;
- non-loopback sockets blocked during measured inference;
- deterministic decoding;
- raw prompt and response retention;
- exact package and hardware metadata; and
- a run-configuration hash that prevents incompatible resume.

The primary experiment begins with text. Whisper and speech-to-mission claims
remain outside the primary experiment until separately evaluated with
consented recordings.

## Metrics

Decision and utility:

- unsafe execution rate on `BLOCK` cases;
- silent continuation rate on `CLARIFY` cases;
- false non-execution rate on `EXECUTE` cases;
- decision accuracy and per-class recall;
- non-empty executable-plan rate; and
- clarification recovery, only if a recovery interaction is implemented.

Plan fidelity:

- JSON/schema validity;
- endpoint validity;
- parameter grounding;
- official-command fidelity; and
- source-task or official-server completion when actually executed.

Containment:

- pre-plan containment;
- post-plan containment;
- parse-error containment; and
- uncontained invalid mission rate.

Compute:

- wall-clock latency;
- input and output tokens;
- model-call count;
- process RAM;
- peak VRAM; and
- NVIDIA GPU-board energy.

GPU-board energy uses a device total-energy counter when available; otherwise,
power is sampled at 20 Hz and numerically integrated. This is not workstation,
simulator, network, or UAV energy.

## Experimental Runs And Statistics

Accuracy:

- one complete locked test run per immutable checkpoint and method when
  decoding is deterministic;
- every expected case-method row retained; and
- failed cases and parse errors included.

Resources:

- 30 source-task clusters, stratified before measurement;
- all five variants for every selected source task;
- three repetitions per model-method condition; and
- resource repetitions reported separately from accuracy.

Statistics:

- source-task-cluster bootstrap;
- paired method differences with confidence intervals;
- a registered primary contrast and primary outcomes; and
- secondary labeling or multiplicity correction for additional comparisons.

## Reproducibility And Readiness Gates

Before the locked run:

- verify the MultiUAV-Plat commit, archive checksum, license, counts, and
  source-task schema;
- remove hard-coded transcription or test-specific aliases;
- prove which NLP component the end-to-end path invokes;
- preserve the registered exclusion of DistilBERT from the primary text-first
  comparison;
- freeze prompts, intervention rules, and method call budgets;
- test that no hidden reference data enters prompts;
- test all output and recursive parameter validators;
- test checkpoint/resume compatibility;
- test that partial source clusters are rejected;
- test that empty plans and empty references are never rewarded;
- label smoke results and exclude them from publication summaries; and
- preserve every raw output and negative result.

## Unresolved Decisions

The following decisions block a locked experiment:

1. **M3 call budget:** Specify whether stage-wise validation uses one or two
   model calls and make M4 exactly compute matched.
2. **Recoverability rule:** Define when missing information requires operator
   clarification versus allowed observation or verification actions.
3. **Execution scope:** Decide whether primary plan fidelity is static or
   includes submission to the official server. Static checks cannot be called
   live mission success.
4. **Review protocol:** Register real author, reviewer, adjudicator, and
   exclusion procedures without fabricating identities.
5. **Hardware protocol:** Register the GPU, precision, sampling mechanism, and
   thermal/warm-up controls for resource measurements.

## Definition Of Done

This revised paper is ready for conclusions only when:

- all source and model checksums are recorded;
- the protocol is frozen before final scores are inspected;
- all five-case source clusters are complete;
- every expected method-case result exists;
- hidden reference fields are absent from prompts;
- trained-component wiring is truthfully documented and tested;
- smoke outputs are excluded from publication tables and figures;
- statistical analysis uses source-task clusters;
- safety, utility, and compute are reported together;
- controlled-derivative, within-Qwen, execution-scope, isolation, and
  call-budget limitations are explicit; and
- the conclusion follows the observed results, including negative or mixed
  findings.
