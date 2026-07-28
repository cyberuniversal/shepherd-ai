# MultiUAV-Plat Session Split Protocol

## Status

This document freezes the source-session split before intervention generation or
model evaluation. It does not freeze task eligibility, variant text, prompts,
labels, or method configurations.

## Source Binding

- Upstream commit:
  `1794e45e421fb5de03094f0b63f9ca95f86ab42f`
- Benchmark archive SHA-256:
  `b5040097d2bfdd44600f3bf486fdb43ee3eb1247fec9c67900b5fcda6feb94a3`
- Split seed: `shepherd-multiuav-split-v1`
- Split manifest: `datasets/multiuav_plat/session_split_v1.json`

## Assignment Algorithm

Sessions are stratified by the upstream `task_type` and the difficulty token in
the paired JSON/JPG filename. The source has 15 strata: three scenario families
by five difficulty levels, with five sessions per stratum.

Within each stratum, sessions are ordered by:

```text
sha256(seed + NUL + session_id), ascending
```

The first three sessions enter `train`, the fourth enters `calibration`, and
the fifth enters `test`. Session ID breaks a cryptographic-hash tie. This gives:

- 45 training sessions;
- 15 calibration sessions; and
- 15 test sessions.

All variants derived from a source task inherit its session split. A source
task cluster may be excluded in full, but it may not be moved between splits
after variant inspection.

## Duplicate-Text Boundary

The source audit found repeated canonical commands and aliases across sessions.
Because duplicate wording connects most sessions into a large graph, grouping
all text-linked sessions is incompatible with the required 45/15/15
stratification.

The session split is therefore frozen independently of task eligibility.
Before variant generation:

1. canonical normalized text occurring across splits must be assigned one
   deterministic owner task and all other complete source-task clusters must be
   excluded;
2. one upstream alias must be selected per retained task without colliding with
   retained canonical or selected alias text in another split;
3. a task with no eligible official alias must be excluded as a complete
   five-case cluster; and
4. exact and normalized overlap must be recomputed on final generated text.

The owner and alias-selection algorithms are not yet frozen. No derivative case
count should be claimed until that next gate is implemented and audited.

## Claim Limits

The split manifest establishes deterministic source-session placement only. It
does not establish independent task wording, valid interventions, balanced
decision labels, model performance, execution success, or the initially
estimated 7,500-case dataset.
