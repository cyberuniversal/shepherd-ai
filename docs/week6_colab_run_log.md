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
