# Final Pipeline Architecture

## Scope

This document is the authoritative architecture statement for the completed
paper experiment. It supersedes historical roadmap descriptions when they
conflict with the final M1-M4 study boundary.

## Final Reported Path

```text
MultiUAV-Plat source tasks (75 sessions, 1,500 tasks)
  -> deterministic eligibility and cross-split leakage checks
  -> controlled five-case intervention clusters
  -> frozen held-out manifest (284 clusters, 1,420 cases)
  -> M1, M2, M3, or M4 with pinned Qwen2.5 3B/7B revisions
  -> strict JSON and API-plan parsing
  -> deterministic evidence, endpoint, command, and grounding validators
  -> score-blind complete-matrix admission
  -> static plan fidelity and containment scoring
  -> source-task-cluster bootstrap and post-hoc session/failure summaries
```

The complete accuracy experiment contains 11,360 admitted method-case rows.
The separate resource campaign contains 3,600 rows across 24 conditions and
three repetitions on one RTX 3090. M4 is described as
**model-call-count-matched**, because it matches M3's number of model calls;
it is not matched for tokens, latency, energy, or prompt length.

## M1-M4 Boundaries

- **M1 monolithic:** one model call produces the decision and plan.
- **M2 deterministic post-plan:** one model call followed by deterministic
  validation.
- **M3 stage-wise:** separate evidence/decision and plan calls with validation
  between stages.
- **M4 model-call-count-matched post-plan:** two model calls followed by
  post-plan validation, controlling model-call count relative to M3.

The versioned implementations are in `src/shepherd_ai/multiuav_methods.py`,
the prompts are in `src/shepherd_ai/multiuav_prompts.py`, and the exact-call
runner and checkpoint logic are in `src/shepherd_ai/multiuav_runner.py` and
`src/shepherd_ai/multiuav_checkpoint.py`.

## Integration Claims

Whisper, DistilBERT, and vision are not integrated into the final M1-M4 path.
They are preserved as preliminary roadmap experiments only:

- Whisper has separate speech-recognition evaluations and never supplies text
  to the frozen MultiUAV accuracy matrix.
- DistilBERT is wired and regression-tested in the historical Shepherd intent
  prototype, but it was trained for span tagging rather than MultiUAV API-plan
  generation and is excluded from M1-M4.
- Agriculture-Vision and VisDrone experiments are separate Week 6 perception
  work. Their outputs are not supplied to the frozen M1-M4 contexts or
  validators.

No final claim relies on those three components. Their retained artifacts show
preliminary implementation, not integration into the reported experiment.

## Execution Boundary

The final experiment did not execute plans against the official MultiUAV
server, a simulator, or physical hardware. Consequently, the paper uses
**static plan fidelity** for command, endpoint, parameter-grounding, and
strict-case success measurements. It does not use “execution success,”
“mission success,” or equivalent operational language for those measurements.

## Evidence Locations

- Complete 3B raw checkpoint: `datasets/multiuav_plat/nautilus/qwen25_3b_accuracy_complete_v1/checkpoint.zip`
- Complete 7B raw checkpoint: `datasets/multiuav_plat/nautilus/qwen25_7b_accuracy_complete_v1/checkpoint.zip`
- Resource raw archive: `datasets/multiuav_plat/nautilus/resource_campaign_attempt3_complete/resource-v1-attempt3-complete.tar.gz`
- Failed and interrupted attempts: `datasets/multiuav_plat/failed_attempts/`
- Scored accuracy rows: `outputs/evaluations/multiuav_accuracy_scoring_v1/`
- Session statistics: `outputs/tables/multiuav_accuracy_session_statistics_v1.csv`
- Failure analysis: `outputs/evaluations/multiuav_accuracy_failure_analysis_v1.json`
- Failure-case identifiers and flags: `outputs/evaluations/multiuav_accuracy_failure_cases_v1.zip`
- Final accuracy/resource tables: `outputs/tables/`
- Final figures: `reports/figures/`

Raw model text remains inside the preserved checkpoints. It is not copied into
the descriptive session or failure artifacts.
