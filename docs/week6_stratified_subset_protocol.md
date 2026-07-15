# Week 6 Train-Label-Stratified Subset Protocol

## Motivation

The fixed seed-17 256-record training subset had zero positive pixels for
`endrow`, `storm_damage`, and `water`. A model trained on that subset cannot
learn those classes. The successful BCE-Dice run learned `drydown`, but all
other evaluated anomaly classes remained at zero IoU.

This experiment changes only training-record selection. Validation records,
model architecture, optimization, loss, seed, and evaluation remain fixed.

## Deterministic Selection

- Start with all official training records.
- Determine image-level anomaly presence from training masks only.
- Rank records deterministically by SHA-256 of seed 17 and relative image path.
- Visit anomaly classes from fewest available positive records to most.
- Reserve up to four hash-ranked positive records per available class.
- Count multi-anomaly images toward every class they contain.
- Fill the remaining 256-record training budget by the original hash ranking.
- Keep the original seed-17 256-record official validation selection.
- Include test references in the manifest for structural reproducibility, but
  do not load test labels during training or evaluation.

Classes absent from the complete training data are reported with zero available
records and are not synthesized.

The first successful scan writes
`outputs/evaluations/week6_agriculture_vision_train_label_presence.json`. This
index contains only image IDs and names of classes with positive training masks;
it contains no pixels or masks. Sixteen parallel readers are used when building
the missing index. Subsequent runs validate the cached class schema and exact
candidate image-ID set before reuse, avoiding repeated mask reads across Colab
runtimes.

The manifest builder also reports a SHA-256 digest of the sorted selected IDs
for each split. The stratified and fixed experiments must have identical
validation digests before their metrics are compared.

## Controlled Training

- Small U-Net from scratch, base channels 16.
- Unweighted masked BCE plus anomaly-only soft Dice, Dice weight 1.0.
- Five epochs, batch size 4, learning rate 0.001, Adam, seed 17.
- Verified Google Colab NVIDIA T4.
- Primary metric: validation modified mIoU.
- Required interpretation: per-class IoU, not aggregate mIoU alone.

## Completion Criteria

- Selector tests pass.
- Selection summary records available and selected positive-image counts.
- The reusable label-presence index passes schema and candidate-ID validation.
- A train-only pixel audit confirms the selected class coverage.
- The fixed validation IDs match the prior 256/256 experiments.
- Five training epochs complete or the failure is preserved.
- Metrics, configuration, checkpoints, hashes, and negative results are stored.

The matched BCE-Dice reference is `0.15387379872696982` best validation modified
mIoU with `drydown` IoU `0.327905255318418`. No invented performance threshold
is used.
