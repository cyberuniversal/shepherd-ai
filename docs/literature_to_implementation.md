# Literature-To-Implementation Rules

The roadmap defines the project sequence and broad deliverables. It does not define safe or rigorous technical implementation details. For implementation choices, use the literature review lessons summarized here and in `AGENTS.md`.

## Core Architecture Rules

- Keep language models at the semantic layer: interpretation, translation, planning proposals, or structured output generation.
- Do not let language models directly control simulated or physical drone dynamics.
- Use bounded, inspectable intermediate representations: JSON mission intents, validated goals, approved action schemas, behavior-tree-like structures, or task graphs.
- Validate generated structures deterministically before they reach planning, scheduling, safety, or execution modules.
- Separate interpretation from execution monitoring. TACOS, Swarm-Steward, CommandSwarm, PROGPROMPT, and the aerial-ground papers all support hierarchical separation.
- Treat format validity as necessary but insufficient. A JSON object, PDDL goal, behavior tree, or Python-like plan can be syntactically valid while still failing the mission.

## Week 2: Speech And Intent Extraction

Technical direction from literature:

- Start with baselines, but do not stop there.
- Build a labeled command dataset with explicit provenance and train/validation/test splits.
- Train or fine-tune the intent extraction component once enough labeled commands exist.
- Keep ASR evaluation separate from intent extraction evaluation.
- Record model name, package version, parameters, random seed, dataset split, and output paths for every experiment.

Roadmap-compatible tools:

- Whisper for speech-to-text.
- spaCy and/or Hugging Face Transformers for intent extraction.

Research constraints:

- Cached transcripts are pipeline smoke checks, not ASR results.
- Synthetic commands are not human speech data.
- No intent extraction accuracy should be reported without held-out labels.

## Week 3: Grounding

Technical direction from literature:

- Use explicit map data first: CSV or GeoJSON with documented regions and coordinates.
- Grounding should return structured records with confidence or ambiguity notes.
- Semantic map and aerial retrieval papers such as VLMaps and GeoText-1652 are relevant background, not solved Shepherd-AI modules.
- Ambiguous terms should trigger explicit failure or clarification, not silent guessing.

## Planning, Scheduling, And Safety

- Planning should consume validated intents and grounded targets.
- Scheduling should use classical allocation baselines before LLM assignment.
- Safety checks must be deterministic and should run before simulated execution.
- Preserve failures and negative results.

## What Not To Claim

Do not claim:

- A trained model exists until training code, data, config, and outputs exist.
- ASR accuracy until real audio and transcripts are evaluated.
- Grounding accuracy until a labeled grounding set exists.
- End-to-end mission success until integrated execution is evaluated.
- Novelty until a formal contribution is written and supported by the literature review.
