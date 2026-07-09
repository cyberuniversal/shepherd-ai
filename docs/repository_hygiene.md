# Repository Hygiene

This repository is a research codebase, not a raw artifact dump. Keep GitHub
usable by separating source-controlled materials from local/generated outputs.

## Track By Default

Track files that define or reproduce the project:

- `src/shepherd_ai/`: reusable package code.
- `scripts/`: reproducible command-line workflows.
- `tests/`: regression and contract tests.
- `notebooks/`: Colab/Jupyter orchestration notebooks.
- `docs/`: roadmap, protocols, acceptance criteria, handoff notes, and design
  decisions.
- `datasets/*/README.md`: dataset documentation.
- Small curated JSONL/CSV/GeoJSON fixtures that are required for tests,
  examples, or benchmark definitions and do not contain private data.
- `pyproject.toml`, `.gitignore`, `README.md`, and root project metadata.

## Do Not Track By Default

Keep these local unless a specific artifact is intentionally promoted into the
research record:

- generated files under `outputs/`,
- generated files under `reports/`,
- model weights and checkpoint directories,
- downloaded public datasets,
- WAV/audio recordings or other private media,
- one-off local helper scripts,
- backup files.

The `.gitignore` keeps generated `outputs/` and `reports/` out of normal
`git status`. Their README files remain trackable so the directory purpose is
documented.

## Promoting An Artifact

If a generated artifact is important enough to commit:

1. Verify it is small enough for Git and contains no private data.
2. Confirm it records source data, model/configuration, split, seed, runtime, and
   caveats where applicable.
3. Prefer documenting the result in `docs/` and keeping raw reproducible outputs
   local.
4. If the raw artifact must be committed, use `git add -f <path>` and mention why
   in the commit message.

## Current Layout

- `datasets/commands/`: small command and intent-label datasets.
- `datasets/maps/`: synthetic map and grounding/planning benchmark fixtures.
- `datasets/sample_audio/`: manifests only; audio files stay local.
- `datasets/aerial_images/`: manifests and documentation only until a licensed
  public subset is selected.
- `outputs/`: raw generated evaluation outputs, ignored by default.
- `reports/`: generated reports and worksheets, ignored by default.

## Branch Layout

Use branches as temporary milestone work lanes:

- `codex/week2-speech-intent`
- `codex/week3-grounding`
- `codex/week4-planning`
- `codex/week5-scheduling`
- `codex/week6-vision`
- `codex/repo-hygiene`

Do not keep long-lived branches that accumulate unrelated roadmap weeks. After a
milestone branch is merged, delete the branch and preserve the milestone state in
`docs/roadmap_status.md`.

## Research Integrity

Ignoring generated artifacts does not mean deleting evidence. Keep local raw
outputs for ongoing work, preserve negative results, and promote only the files
that are necessary for reproducibility or review.
