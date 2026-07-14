# Week 6 Fixed Held-Out Development Protocol

## Objective

Evaluate whether scaling the Agriculture-Vision development experiment from
64 training and 64 validation tiles to 256 training and 256 validation tiles
improves the overlap-aware segmentation result without changing the model or
using validation information during training.

This remains a development experiment. It is not a final Agriculture-Vision
benchmark and does not use test labels.

## Fixed Data Selection

- Dataset: Agriculture-Vision 2017 miniscale.
- Manifest: `datasets/aerial_images/manifest_segmentation_seed17_dev256.jsonl`.
- Selection: deterministic SHA-256 ranking with seed 17.
- Training input: up to 256 records from the official training split.
- Held-out evaluation input: up to 256 records from the official validation
  split.
- Test labels: not loaded.
- Raw imagery and labels remain outside Git in the private Google Drive cache.

The selection was defined before this training run. The validation subset must
not be used to derive loss weights, select training examples, or update model
parameters.

## Training Configuration

- Runtime: Google Colab NVIDIA T4.
- Model: the repository's small U-Net segmentation baseline.
- Base channels: 16.
- Epochs: 5.
- Batch size: 4.
- Learning rate: 0.001.
- Random seed: 17.
- Loss: unweighted binary cross-entropy over the configured output channels.
- Checkpoints: private Google Drive Week 6 checkpoint directory.

The unweighted loss is retained because the recorded cap-20 class-weighted
comparison underperformed both unweighted 64/64 controls.

## Outputs And Evaluation

The primary metric is validation modified mIoU. The run must also preserve:

- per-epoch training loss,
- per-epoch validation loss,
- per-epoch validation modified mIoU,
- per-class validation IoU,
- validation confusion counts and valid-pixel count,
- training configuration,
- best and last checkpoints,
- runtime and device metadata.

The comparison reference is the prior unweighted 64/64 T4 development result,
whose best validation modified mIoU was `0.09651361447267072`. Improvement is a
research outcome, not a completion requirement.

## Completion Criteria

The experiment is complete when:

- the selected manifest contains the fixed training and validation subsets,
- training runs on a verified T4 and uses no validation or test record for
  parameter updates,
- all five epochs complete or a failure is preserved with its cause,
- raw metrics and checkpoints are preserved in the private experiment store,
- a tracked summary records the exact configuration and results,
- the result is explicitly labeled as validation-only development evidence.

No performance threshold is preregistered because the repository documents do
not establish a defensible threshold for this experiment.
