# Week 6 Segmentation Development Protocol

## Purpose

Agriculture-Vision requires semantic segmentation rather than generic object
detection. This protocol defines the first trainable Week 6 baseline and
validates training, checkpointing, and modified-mIoU before larger experiments
consume additional T4 time.

## Technical Decisions

- Model: compact U-Net trained from scratch. This is an inspectable baseline,
  not a novelty claim.
- Input: RGB tiles converted to floating point in the range 0 to 1.
- Target: derived background plus all nine potentially overlapping anomaly
  masks.
- Loss: binary cross entropy with logits over evaluation-valid pixels. A
  single-label target would discard overlapping annotations.
- Development prediction map: maximum-logit class at each pixel.
- Metric: the repository's overlap-aware modified mIoU.
- Seed: 17.
- Device gate: a CUDA device whose name contains `T4`.
- Checkpoints: `last.pt` after every epoch and `best.pt` when validation
  modified mIoU improves.

## Initial Development Run

- 64 official training records.
- 64 official validation records.
- Test records may remain in the manifest, but their masks are not loaded.
- 3 epochs, batch size 4.
- Adam optimizer with learning rate 0.001.
- Base channel width 16.

This is a pipeline-validation run, not final benchmark performance.

The initial run used the manifest builder's sorted-prefix selection and showed
strong background dominance. Follow-up development manifests must use
`--selection-strategy seeded-hash --selection-seed 17`, then run the label
audit before training. This removes filesystem ordering as the subset-selection
rule while keeping the exact sample reproducible. It does not guarantee class
balance, so the recorded audit determines whether sampling or loss changes are
needed.

## Leakage Controls

- Official farmland-level split metadata remains authoritative.
- Training consumes only `train` records.
- Checkpoint selection consumes only `validation` records.
- The training script never loads test masks.
- Test evaluation remains deferred until architecture, preprocessing, and
  hyperparameters are fixed.

## Recorded Artifacts

- Configuration, dependency versions, and device metadata.
- Epoch-level training and validation loss.
- Validation per-class IoU, modified mIoU, confusion matrix, and valid pixels.
- Last and best checkpoints with optimizer state and history.
- Failed runs and negative results in the Week 6 run log.

## Success Criteria

The development run succeeds when all epochs complete on a T4, resumable
checkpoints and metrics are written to private Drive storage, test masks remain
unused, and validation loss and modified mIoU are finite. The repository does
not state a minimum performance threshold.
