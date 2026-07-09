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

## Literature-Driven Rules

The literature review warns that perception and vision-language demos can look
promising without proving reliable mission execution. Week 6 therefore treats
detections as one bounded module output. Detection summaries are not mAP, recall,
or downstream task success unless labeled data and a formal evaluation protocol
are added.

## Current Data Status

No public aerial dataset has been selected, downloaded, licensed, split, or
preprocessed in the repository.

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

Install the optional vision dependencies before real inference:

```powershell
python -m pip install -e .[vision]
```

Run YOLO detection on the validated manifest:

```powershell
python scripts/run_yolo_detection.py --manifest datasets/aerial_images/manifest.jsonl --dataset-root . --model yolov8n.pt --predictions-output outputs/evaluations/week6_yolo_detections.jsonl --summary-output outputs/evaluations/week6_yolo_detection_summary.json --annotated-dir outputs/visualizations/week6_yolo
```

## Current Implementation

Primary module:

- `src/shepherd_ai/vision.py`

Primary scripts:

- `scripts/validate_vision_manifest.py`
- `scripts/run_yolo_detection.py`

Tests:

- `tests/test_vision.py`
- `tests/test_validate_vision_manifest_cli.py`

## Evaluation

Current available metrics:

- manifest record counts,
- split/source/data-type/license counts,
- detection counts by class after YOLO inference.

Not evaluated:

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

The full Week 6 roadmap slice is not complete until a licensed aerial-image
subset exists and at least one documented inference run is recorded.
