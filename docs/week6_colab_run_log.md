# Week 6 Colab Run Log

## Run 2026-07-11 - CPU Backend Rejected

Status: failed before inference; preserved negative infrastructure result.

Repository commit:

- `09deec5c666865f24a748f7d78bede6d1fb896f6`

Dataset preparation:

- source: Agriculture-Vision CVPR 2020 official IntelinAir AWS bucket,
- archive: `data2017_miniscale.tar.gz`,
- archive SHA-256: `2b4bf0b2357ba982fe6d81da55841874afdd721a867bb8fddede9e04e4914027`,
- selected manifest records: 30,
- source splits: 10 train, 10 validation, 10 test,
- records with image SHA-256: 30,
- records with labels in the YOLO manifest: 0.

Requested inference:

- model: `yolov8n.pt`,
- confidence threshold: `0.25`,
- requested device: `0`,
- Ultralytics: `8.4.92`,
- Python: `3.12.13`,
- observed PyTorch: `2.11.0+cpu`.

Observed failure:

- `torch.cuda.is_available()` was `False`,
- CUDA device count was `0`,
- Ultralytics rejected `device=0` before processing any image.

Interpretation:

- no YOLO inference occurred,
- no detections or annotated outputs were produced,
- this is not a model-performance result,
- the notebook was corrected in commit `6d24592` to verify an actual T4 before
  downloading the dataset and to persist CUDA device metadata in future YOLO
  summaries.

## Run 2026-07-12 - T4 Smoke Test Completed

Status: completed; raw non-image outputs preserved in the repository.

Repository commit:

- `08610826d7bca46ed16b8e402f1225bd910dc850`

Runtime:

- accelerator: NVIDIA Tesla T4,
- observed PyTorch: `2.11.0+cu128`,
- Ultralytics package version: not recorded by this run,
- model: `yolov8n.pt`,
- confidence threshold: `0.25`,
- requested device: `0`,
- required device-name substring: `T4`.

Dataset preparation:

- source: Agriculture-Vision CVPR 2020 official IntelinAir AWS bucket,
- archive: `data2017_miniscale.tar.gz`,
- archive SHA-256: `2b4bf0b2357ba982fe6d81da55841874afdd721a867bb8fddede9e04e4914027`,
- selected manifest records: 30,
- source splits: 10 train, 10 validation, 10 test,
- records with image SHA-256: 30,
- records with labels in the YOLO manifest: 0.

Observed smoke-test output:

- images processed: 30,
- detections: 1,
- detected class: `person`,
- detection confidence: `0.25596851110458374`,
- raw predictions: `outputs/evaluations/week6_yolo_detections.jsonl`,
- run summary: `outputs/evaluations/week6_yolo_detection_summary.json`,
- manifest summary: `outputs/evaluations/week6_vision_manifest_summary.json`.

Downloaded artifact archive:

- local filename: `week6_vision_t4_artifacts.zip`,
- archive SHA-256: `c70fc8a16c215419f260e858c04f6f3e2274e50f5a1bfbe4d9801898884213b5`,
- contents: three evaluation files and 30 annotated images,
- annotated images remain local and are not committed because the source dataset
  terms prohibit redistribution.

Interpretation:

- the T4-gated inference and artifact-export paths worked,
- the single detection is a pipeline output, not evidence of Agriculture-Vision
  anomaly-detection performance,
- mAP, precision, recall, and class-specific performance were not evaluated
  because this manifest contains no YOLO-compatible ground-truth labels,
- the generic COCO-pretrained YOLO smoke test does not address the semantic
  segmentation task defined by Agriculture-Vision,
- no model training or fine-tuning occurred in this run.
