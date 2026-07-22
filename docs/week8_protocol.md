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
5. Distinguish navigable search regions from perception targets. A command such
   as `search for a car in the east field` may use East Field coordinates as a
   bounded search region, but it must not assign coordinates to the car. The
   object remains `awaiting_vision`, and the simulator executes an inspectable
   region sweep until mission imagery is available.
6. Schedule all three task replicas together, then run deterministic preflight
   and event-driven supervision using the Week 7 interfaces.
7. Run vision inference on the images registered to this mission. Prior Week 6
   results may establish model provenance but are not mission observations.
8. Write raw stage outputs before deriving metrics or a mission report.
9. Mark the run incomplete whenever required evidence is absent or a stage is
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

## Recorded Completion Evidence

The Colab run completed on 2026-07-22 and the machine-checked audit passes all
ten gates with no blockers. Registered evidence includes the exact human WAV
and its hash, Whisper prediction and WER, frozen trained-intent predictions,
the resolved three-drone schedule, safety report, 43 telemetry records,
mission-assigned image manifest, raw segmentation predictions, five-metric
summary, animated map, log, screenshot, and mission report.

The roadmap does not state metric acceptance thresholds or baseline
comparisons, so completion means that the required stages and measurements are
present and traceable, not that every measured value is strong. In particular,
the 59-image Agriculture-Vision validation-remainder evaluation recorded
mission-class modified mean IoU `0.02356`. The project-defined mapping uses
non-water anomaly classes for crop inspection and `water` plus `waterway` for
irrigation inspection; this mapping, the weak result, and the internal-
validation limitation must be reported. The discontinued 3D experiments do
not supply active mission evidence.

The machine-checked artifact schema is documented in
`docs/week8_evidence_contract.md`.

## Recorded Destination Resolution

On 2026-07-16, the operator selected East Field for the third drone. The stored
resolution is `clause_002=loc_east_field`. This permits the typed preparation
and deterministic movement simulation to proceed without rewriting the fixed
roadmap command or moving the existing Irrigation Canal map record.
