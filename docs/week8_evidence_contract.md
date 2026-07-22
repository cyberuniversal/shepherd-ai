# Week 8 Evidence Contract

## Purpose

Week 8 must join independently stored stage evidence without relabeling a
typed command, development image, or module benchmark as an end-to-end result.
`scripts/audit_week8_completion.py` enforces this contract.

## Exact-Scenario ASR

`outputs/evaluations/week8_exact_scenario_asr.json` must contain:

- `scenario_source`: `roadmap_week8_fixed_scenario`;
- the exact roadmap reference transcript and the model prediction;
- a human-recorded audio path, SHA-256, and `human_recorded_audio` data type;
- Whisper model name, version, parameters, package versions, and runtime;
- word error rate and exact-match values derived from the stored texts.

A typed command, cached transcript without the WAV, or synthesized voice does
not satisfy this stage.

## Trained Intent Evidence

`outputs/evaluations/week8_exact_scenario_intent_evaluation.json` must contain
two clause records, gold fields traceable either to human verification or the
fixed roadmap specification, predictions from the frozen trained checkpoint,
exact model identity/hash, and exact-match accuracy. The
deterministic parser may remain a baseline or validator but cannot be presented
as the trained result.

## Mission Vision Evidence

`outputs/evaluations/week8_mission_vision_evaluation.json` must identify every
mission image, clause assignment, source, license/access note, split, file hash,
label provenance, frozen model hash, inference parameters, raw prediction path,
and metric denominator.

The roadmap does not state how crop and irrigation inspection map to detector
classes. The registered Week 8 protocol uses a disjoint remainder of the
Agriculture-Vision validation split with the frozen Week 6 segmentation
checkpoint. Crop inspection covers the non-water agricultural anomaly classes;
irrigation inspection covers `water` and `waterway`. This mapping is a declared
Shepherd-AI protocol choice, not a claim made by the dataset authors. VisDrone
person/vehicle classes must not be treated as crop or irrigation findings.

No image used for model training, checkpoint selection, hyperparameter choice,
or Week 6 development comparison may enter the Week 8 holdout. The selector
excludes every ID in the fixed Week 6 development manifest before choosing
label-positive records by a seeded hash. This is an internal validation
remainder, not the official hidden test benchmark. If a provably disjoint
labeled set cannot be constructed, detection performance is `not evaluated`
and Week 8 remains incomplete.

## Metrics

`outputs/evaluations/week8_end_to_end_evaluation.json` must report the five
roadmap metrics with a numeric value, denominator, definition, and source
artifact:

- intent extraction accuracy;
- grounding accuracy;
- scheduling quality;
- detection performance;
- overall execution time.

The summary must explicitly set physical-flight, safety-guarantee, and novelty
claims to false. Missing metrics are not converted to zero.

## Reports And Demonstration Artifacts

The final gate also requires the raw run, telemetry, animated map, derived
evaluation summary, mission report, demonstration log, and screenshot. Derived
reports must remain traceable to raw inputs by path and SHA-256.
