# Week 8 End-to-End Protocol

## Why Week 8 Comes Next

The corrected Week 7 audit permits advancement. Week 8 is the roadmap's first
complete-system milestone and must run the exact compound scenario through
speech, intent extraction, grounding, planning, scheduling, safety, vision, and
reporting. The literature review requires bounded intermediate representations,
deterministic validation, closed-loop monitoring, and a distinction between
format-valid outputs and mission success.

## Fixed Scenario

> Send two drones north to inspect crops and one drone east to inspect irrigation.

The command contains two mission clauses and requests three drones. A single
intent with count three is not an acceptable representation because it loses
the separate destinations and targets.

## Inputs

- One human-recorded WAV of the fixed scenario with a human-written reference
  transcript. This input is not currently present.
- The existing custom synthetic map, three-drone simulated fleet, and synthetic
  Week 7 safety policy.
- Images explicitly assigned to the north-field crop task and irrigation task,
  with source, license/access note, split, and file hashes. A mission image
  manifest is not currently present.
- Frozen model artifacts and inference parameters for ASR, intent extraction,
  and vision.

## Execution Rules

1. Store the ASR prediction separately from the reference transcript and score
   transcription before intent extraction.
2. Decompose only explicit mission-clause boundaries. Unsupported compounds
   require clarification rather than guessed segmentation.
3. Parse, ground, and plan each clause independently while retaining its source
   clause identifier.
4. Reconcile multiple map references. The map grounds `east` to East Field and
   `irrigation` to Irrigation Canal at a different location. The operator
   explicitly selected East Field as the destination; irrigation remains the
   semantic inspection target, and the original references remain in the raw
   record.
5. Schedule all three task replicas together, then run deterministic preflight
   and event-driven supervision using the Week 7 interfaces.
6. Run vision inference on the images registered to this mission. Prior Week 6
   results may establish model provenance but are not mission observations.
7. Write raw stage outputs before deriving metrics or a mission report.
8. Mark the run incomplete whenever required evidence is absent or a stage is
   blocked. Preserve that negative result.

## Evaluation

The roadmap requires intent extraction accuracy, grounding accuracy, scheduling
quality, detection performance, and overall execution time. The roadmap does
not state acceptance thresholds, so Week 8 will report measured values and
their denominators without inventing pass criteria. Module-level development
metrics remain separate from the single-scenario end-to-end outcome.

## Success Condition

Week 8 is complete only when the fixed scenario has a reproducible stored run
covering every required stage, actual speech and mission-assigned images have
provenance, the two clauses and three assignments are preserved, safety does not
approve unresolved evidence, all required metrics are reported, and the mission
report, log, and screenshots trace back to raw outputs.

## Current Known Blockers

- No WAV recording of the exact fixed scenario is registered.
- `datasets/aerial_images/manifest.jsonl` does not exist, and only the dataset
  README is present under that directory.
- Metric acceptance thresholds and baseline comparisons are not stated.

## Recorded Destination Resolution

On 2026-07-16, the operator selected East Field for the third drone. The stored
resolution is `clause_002=loc_east_field`. This permits the typed preparation
and deterministic movement simulation to proceed without rewriting the fixed
roadmap command or moving the existing Irrigation Canal map record.
