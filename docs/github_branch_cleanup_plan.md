# GitHub Branch Cleanup Plan

This plan makes GitHub match the roadmap without rewriting project history.

## Current Situation

The repository currently has long-lived branches that reflect how work happened:

- `main`: initial foundation.
- `codex/week-2-speech-input`: early Week 2 speech-input work.
- `codex/colab-literature-structure`: later work that accumulated multiple
  roadmap weeks.
- `colab-literature-structure`: duplicate remote branch name without the
  `codex/` prefix.
- `codex/roadmap-repo-hygiene`: current cleanup branch.

## Desired Branch Model

Keep only:

- `main`: clean milestone history.
- one active `codex/weekN-*` or `codex/repo-*` branch at a time.

Recommended branch names:

- `codex/week2-speech-intent`
- `codex/week3-grounding`
- `codex/week4-planning`
- `codex/week5-scheduling`
- `codex/week6-vision`
- `codex/week7-safety-integration`
- `codex/repo-hygiene`

## Cleanup Sequence

1. Merge the current roadmap/repo-hygiene cleanup into `main`.
2. Confirm `main` contains `docs/roadmap_status.md` and no tracked generated
   artifact dump under `outputs/` or `reports/`.
3. Delete stale duplicate remote branches after their work is represented on
   `main`.
4. Use future branches only for the active roadmap milestone.

## Branches To Delete After Merge

Delete only after confirming their work is on `main`:

- `origin/colab-literature-structure`
- `origin/codex/colab-literature-structure`
- `origin/codex/week-2-speech-input`

Do not delete branches before the merge is verified.
