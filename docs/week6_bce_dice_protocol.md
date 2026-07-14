# Week 6 BCE-Dice Comparison Protocol

## Reason For The Comparison

The fixed seed-17 256/256 unweighted BCE run reduced both training and
validation loss but produced zero IoU for every evaluated anomaly class at its
best epoch. More images and epochs did not prevent background collapse. The
cap-20 positive-weight experiment also underperformed the unweighted baseline.

This comparison changes only the training objective. It does not change the
data selection, model, optimizer, seed, or evaluation metric.

## Fixed Inputs

- Agriculture-Vision 2017 miniscale.
- Deterministic seed-17 manifest with 256 train and 256 validation records.
- Complete train-only label audit for determining which classes exist in
  training data.
- No validation prevalence or test labels used to construct the objective.

## Objective

The experimental loss is:

`unweighted masked BCE + 1.0 * anomaly-only masked soft Dice`

The BCE term remains active for all configured output channels. The Dice term:

- excludes background,
- excludes classes with zero positives in the complete training split,
- aggregates overlap over each batch and valid field pixels,
- averages only over active anomaly classes,
- uses smoothing constant 1.0.

## Controlled Configuration

- Model: small U-Net from scratch, base channels 16.
- Epochs: 5.
- Batch size: 4.
- Learning rate: 0.001.
- Optimizer: Adam.
- Random seed: 17.
- Runtime: verified Google Colab NVIDIA T4.
- Primary metric: validation modified mIoU.

## Completion And Interpretation

The run is complete when the T4 PyTorch tests pass, all five epochs finish or a
failure is preserved, and metrics/configuration/checkpoint hashes are recorded.

The primary comparison is against the fixed 256/256 BCE best validation
modified mIoU of `0.0925782719754147`. Anomaly-class IoU must be inspected
separately: an increased mean driven only by background is not evidence that
the collapse was corrected. No success threshold is invented.
