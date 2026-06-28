# Shepherd-AI

Shepherd-AI is a planned Python research prototype for natural-language multi-drone mission planning and coordination in software simulation.

Current status: this repository contains project source documents, a deterministic typed-command intent parser baseline, and a speech-input scaffold for audio manifest validation and transcript evaluation. It is not an end-to-end prototype, does not control physical drones, and does not yet implement Whisper inference, grounding, planning, scheduling, vision, safety validation, or integrated mission execution.

## Source Documents

The current source of truth is:

- `AGENTS.md`
- `docs/roadmap.pdf`
- `docs/literature_review/ExportBlock-44375080-06b3-45d5-a3ed-ac880ba80cd6-Part-1.zip`
- `docs/project_synthesis.md`
- `docs/implementation_plan.md`
- `docs/milestone_2_speech_input.md`

The roadmap path is `docs/roadmap.pdf`; there is currently no `docs/roadmap/` directory.

## First Milestone

The first implemented milestone is a typed-command intent extraction baseline from Week 2 of the roadmap. It accepts simple typed mission commands and emits JSON fields aligned with the roadmap: `action`, `count`, `location`, `target`, and `constraints`.

Audio support is deferred because the repository has no sample WAV files, transcripts, Whisper configuration, package versions, or evaluation split.

## Speech Input Scaffold

Milestone 2 currently validates audio/transcript manifests and evaluates transcript text. It does not run Whisper yet.

Manifest records should point to WAV files under the dataset root and include transcript provenance fields. See `docs/milestone_2_speech_input.md`.

## Run Tests

Use Python from the repository root:

```powershell
python -m unittest discover -s tests
```

## Run Example

```powershell
python examples/intent_baseline_example.py
```

## Run Initial Evaluation

```powershell
python scripts/evaluate_intent_baseline.py
```

The evaluation writes raw output to `outputs/evaluations/intent_baseline_roadmap_examples.json`. The included sample is roadmap-derived and synthetic; it is a smoke check, not a research benchmark.
