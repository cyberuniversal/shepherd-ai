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

## Run 2026-07-12 - 2017 Label Layout Audit

Status: completed; non-image layout summary preserved in the repository.

Repository commit:

- `5fe4aba42b752dd8c2f4ff152f8e90bc19af7d8a`

Runtime and source:

- accelerator: NVIDIA Tesla T4,
- observed PyTorch: `2.11.0+cu128`,
- archive SHA-256: `2b4bf0b2357ba982fe6d81da55841874afdd721a867bb8fddede9e04e4914027`,
- terms acknowledgment was entered by the user for this Colab session.

Observed layout:

- 8,345 aligned tiles,
- RGB: 8,345 JPEG files, mode `RGB`, shape 512 x 512,
- NIR: 8,345 JPEG files, mode `L`, shape 512 x 512,
- field boundaries: 8,345 binary PNG files,
- field masks: 8,345 binary PNG files,
- nine anomaly directories with 8,345 binary PNG files each,
- observed mask values: `0` and `255`.

Observed anomaly directories:

- `double_plant`,
- `drydown`,
- `endrow`,
- `nutrient_deficiency`,
- `planter_skip`,
- `storm_damage`,
- `water`,
- `waterway`,
- `weed_cluster`.

Interpretation:

- all modalities and masks align by image stem,
- background is derived where no anomaly mask is active,
- evaluation-valid pixels are the intersection of `field_bounds` and
  `field_masks`,
- overlapping anomaly masks must remain multilabel ground truth,
- no segmentation model was trained and no dataset-backed mIoU was calculated
  in this audit.

## Run 2026-07-12 - Label Audit Blocked By Recycled Runtime

Status: failed before label audit; preserved negative infrastructure result.

Requested operation:

- update the Colab checkout to commit `aa673c2`,
- audit the 10 train and 10 validation manifest records,
- exclude all 10 test records.

Observed failures:

- the first ad hoc command ran outside the repository and Git rejected it,
- the corrected command used `/content/shepherd-ai` explicitly,
- Colab then reported that `/content/shepherd-ai` no longer existed,
- therefore the temporary dataset, manifest, and generated outputs had been
  removed when the runtime was recycled.

Interpretation:

- no train, validation, or test labels were audited in this attempt,
- no prevalence or overlap result was produced,
- no model training occurred,
- the acquisition and terms-acknowledgment workflow must be rerun in a fresh
  T4 session before executing the committed label-audit command.

## Run 2026-07-13 - Drive-Backed T4 Smoke Test Reproduced

Status: completed; raw non-image outputs preserved in the operator's private
Google Drive cache.

Repository commit:

- `fa069d5730edfc1736f4cfa6795e26bcdafe63d0`

Runtime and input:

- accelerator: NVIDIA Tesla T4,
- observed PyTorch: `2.11.0+cu128`,
- manifest records: 30,
- split counts: 10 train, 10 validation, 10 test,
- records with image SHA-256: 30,
- model: `yolov8n.pt`,
- confidence threshold: `0.25`,
- device: CUDA device `0`,
- generated at: `2026-07-13T13:55:56.508883+00:00`.

Observed output:

- images processed: 30,
- detections: 1,
- detected class: `person`,
- raw predictions: `week6_yolo_detections.jsonl`,
- summary: `week6_yolo_detection_summary.json`,
- persistent location: private Google Drive directory
  `MyDrive/shepherd-ai-private/week6/`.

Interpretation:

- the Drive-backed cache avoided another dataset download,
- the manifest and T4 device gates passed,
- the result reproduces the prior generic YOLO smoke-test behavior,
- this is a detection-count pipeline check, not Agriculture-Vision anomaly
  segmentation performance,
- no segmentation model was trained or evaluated in this run.

## Run 2026-07-13 - Agriculture-Vision Segmentation Development Baseline

Status: completed; development result, not a final benchmark.

Repository commit:

- `7b0f5d1` (`Add Week 6 segmentation development baseline`)

Runtime and configuration:

- accelerator: NVIDIA Tesla T4,
- PyTorch: `2.11.0+cu128`,
- NumPy: `2.0.2`,
- model: compact U-Net trained from scratch,
- outputs: background plus nine Agriculture-Vision anomaly channels,
- loss: masked multilabel BCE with logits,
- split: 64 train tiles, 64 validation tiles, zero test masks,
- epochs: 3,
- batch size: 4,
- learning rate: `0.001`,
- base channels: 16,
- random seed: 17,
- input normalization: RGB values divided by 255.

Observed validation result:

- train loss by epoch: `0.742691`, `0.677485`, `0.640324`,
- validation loss by epoch: `0.710684`, `0.639761`, `0.604306`,
- modified mIoU by epoch: `0.000000`, `0.071016`, `0.096514`,
- best validation modified mIoU: `0.09651361447267072`,
- final background IoU: `0.8022135341731719`,
- final drydown IoU: `0.06640899608086455`,
- all other evaluated anomaly classes: `0.0`,
- water IoU: not evaluated because no water target pixels occurred in this
  validation subset,
- valid validation pixels per epoch: 14,698,298.

Tracked non-image evidence:

- `outputs/evaluations/week6_segmentation_dev64_training_config.json`,
- `outputs/evaluations/week6_segmentation_dev64_metrics_summary.json`.

Private Drive artifacts and SHA-256:

- `training_config.json`: `7813f8c556778c8c9ae4b2399dab62d05d7d3c26d8bcc57c1e371f3fecd93c65`,
- `metrics.json`: `88aedd6c83934caefaf46be2437aa7e31e840d61662b33ddf5f2b303559616f2`,
- `best.pt`: `b1638133c9b043b9e713dda1509d815c05d6309abf6c374bafbe4260c6f59095`,
- `last.pt`: `1124ef177d55042927904f040694cfdd1ecf012553e859d37e0c651803bb689d`.

Interpretation:

- the full train/checkpoint/evaluate path ran successfully on a T4,
- decreasing train and validation losses confirm optimization occurred,
- performance is dominated by background and the model has not learned most
  anomaly classes on this small, imbalanced three-epoch subset,
- this negative class-level result motivates class-aware sampling, loss
  comparison, and a larger development split before fixed held-out evaluation,
- no test labels were loaded, so the held-out test protocol remains untouched.
