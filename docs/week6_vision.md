# Week 6 Computer Vision

## Scope

Week 6 begins the roadmap item "Computer Vision Integration." The current
implementation establishes the reproducible input and output contract for
aerial-image detection:

- validate a manifest of licensed aerial images,
- run Ultralytics YOLO only when real image files and the optional vision
  dependencies are present,
- write raw detection rows separately from detection summaries,
- record model name, parameters, dataset provenance, and caveats.

This is not mission success, safety validation, tracking, route planning,
physical-drone perception, or a detection-performance benchmark.

The first Colab attempt attached a CPU-only backend and was rejected before
inference. A later T4 run processed 30 images and preserved its raw non-image
outputs. Both runs are recorded in `docs/week6_colab_run_log.md`.

## Literature-Driven Rules

The literature review warns that perception and vision-language demos can look
promising without proving reliable mission execution. Week 6 therefore treats
detections as one bounded module output. Detection summaries are not mAP, recall,
or downstream task success unless labeled data and a formal evaluation protocol
are added.

## Current Data Status

Agriculture-Vision CVPR 2020 is selected for the first experiment. It was
downloaded into a temporary Colab session after the user accepted the official
terms. The repository does not redistribute the dataset or annotated images.
Its terms allow limited non-commercial research use and prohibit
redistribution. See `docs/week6_dataset_decision.md`.

The repository implements the overlap-aware modified-mIoU rule in
`modified_multilabel_iou`. It accepts a single predicted class map, a stack of
potentially overlapping target masks, and an optional valid-pixel mask. Empty
classes are reported explicitly and excluded from the mean. The exact 2017
archive label-directory mapping is implemented for the observed miniscale
layout. The trainable development protocol is documented in
`docs/week6_segmentation_protocol.md`.

The 2017 layout audit is preserved at
`outputs/evaluations/week6_agriculture_vision_layout_summary.json`. It records
8,345 aligned RGB, NIR, boundary, valid-mask, and nine-class anomaly-mask files.
It contains no licensed image pixels.

Supported manifest location:

- `datasets/aerial_images/manifest.jsonl`

Each JSONL record must include:

- `id`
- `image_path`
- `split`
- `source`
- `data_type`
- `license`
- `provenance_url`

Optional fields:

- `labels_path`
- `notes`
- `sha256`
- `terms_url`

Allowed image suffixes:

- `.jpg`
- `.jpeg`
- `.png`

Allowed splits:

- `train`
- `validation`
- `test`
- `demo`

## Reproducible Commands

Validate an aerial-image manifest:

```powershell
python scripts/validate_vision_manifest.py --manifest datasets/aerial_images/manifest.jsonl --dataset-root . --summary-output outputs/evaluations/week6_vision_manifest_summary.json
```

After an official Agriculture-Vision archive has been downloaded and extracted,
build a deterministic RGB subset manifest:

```powershell
python scripts/prepare_agriculture_vision_subset.py --dataset-dir datasets/aerial_images/agriculture-vision --dataset-root . --split-json datasets/aerial_images/agriculture-vision/data2017_splits.json --output datasets/aerial_images/manifest.jsonl --max-per-split 10 --accept-terms
```

Install the optional vision dependencies before real inference:

```powershell
python -m pip install -e .[vision]
```

Run YOLO detection on the validated manifest:

```powershell
python scripts/run_yolo_detection.py --manifest datasets/aerial_images/manifest.jsonl --dataset-root . --model yolov8n.pt --device 0 --required-device-substring T4 --predictions-output outputs/evaluations/week6_yolo_detections.jsonl --summary-output outputs/evaluations/week6_yolo_detection_summary.json --annotated-dir outputs/visualizations/week6_yolo
```

## Current Implementation

Primary module:

- `src/shepherd_ai/vision.py`

Primary scripts:

- `scripts/validate_vision_manifest.py`
- `scripts/run_yolo_detection.py`
- `scripts/prepare_agriculture_vision_subset.py`
- `scripts/inspect_agriculture_vision_layout.py`
- `scripts/validate_agriculture_vision_labels.py`
- `scripts/train_agriculture_vision_segmentation.py`

Tests:

- `tests/test_vision.py`
- `tests/test_validate_vision_manifest_cli.py`
- `tests/test_inspect_agriculture_vision_layout_cli.py`
- `tests/test_validate_agriculture_vision_labels_cli.py`

## Evaluation

Current available metrics:

- manifest record counts,
- split/source/data-type/license counts,
- detection counts by class after YOLO inference.
- overlap-aware per-class IoU and modified mIoU for supplied class maps and
  overlapping target-mask stacks.

Not evaluated on Agriculture-Vision labels:

- mAP,
- precision,
- recall,
- public benchmark performance,
- mission success,
- safety impact.

## Completion Criteria For This Slice

This initial Week 6 foundation is complete when:

- image manifests require explicit provenance and license fields,
- image and optional label paths must stay inside the dataset root,
- manifest validation writes raw summary output,
- YOLO inference records model parameters and raw detection rows,
- detection summaries state that they are not benchmark performance,
- tests cover manifest validation and detection-summary behavior.

The original foundation gate has been exercised on a T4 and its non-image raw
outputs are preserved. The first segmentation development baseline was also
trained on a T4 using 64 train and 64 validation tiles, three epochs, and seed
17. Its best validation modified mIoU was `0.0965`, dominated by background;
most anomaly classes remained at zero. Week 6 remains incomplete as a
research-quality vision milestone until the development experiment is scaled,
class imbalance is addressed through recorded comparisons, and a fixed
held-out protocol is evaluated. YOLO inference on Agriculture-Vision is a smoke
test, not its semantic-segmentation benchmark.
