# Repository Instructions

This repository contains the frozen validation-placement publication study. It
does not contain the roadmap-based Shepherd-AI ISEF system.

## Source Of Truth

Before changing research code, data, results, or manuscript claims, read:

- `paper/main.tex`
- `docs/code_plan_compliance.md`
- every `docs/multiuav_*.md` protocol
- `docs/final_pipeline_architecture.md`
- `docs/final_reproduction_commands.md`
- the applicable manifests and admission records under
  `datasets/multiuav_plat/` and `outputs/`

## Frozen Scope

- Do not add modules, baselines, models, datasets, or research directions.
- Use `model-call-count-matched` for M4.
- Use `static plan fidelity`; no official simulator or physical execution was
  performed.
- Do not claim Whisper, DistilBERT, or vision as part of M1-M4.
- Preserve raw output separately from derived analysis.
- Preserve failed runs, negative results, immutable model revisions, checksums,
  execution commits, session IDs, and seeds.
- Do not inspect hidden labels before the registered admission gate.
- Do not fabricate or silently repair experimental evidence.

## Development

- Keep code typed and provider-independent at the experiment boundary.
- Add or update focused tests for every behavioral change.
- Run the checks documented in `docs/final_reproduction_commands.md`.
- Do not commit credentials, model weights, private data, or upstream content
  whose redistribution rights are not established.

