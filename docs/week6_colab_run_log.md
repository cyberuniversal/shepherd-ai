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

## Run 2026-07-13 - Seeded Development Audit Blocked

Status: blocked before data access; preserved infrastructure result.

Repository commit:

- `d69d448` (`Add reproducible Week 6 subset sampling`)

Requested operation:

- build a deterministic hash-ranked sample with seed 17,
- select up to 256 records from each official split,
- audit only the 256 train and 256 validation label sets,
- use the observed class coverage to choose the next controlled training
  comparison.

Observed blockers:

- Colab rejected a new GPU runtime because the account had reached its current
  GPU usage limit,
- a CPU runtime was connected only for preprocessing and label audit,
- the private Google Drive cache remount timed out after two minutes with
  `ValueError: mount failed`.

Interpretation:

- no seeded manifest or label-audit result was produced in this attempt,
- no model training was attempted on CPU,
- the completed 64/64 T4 baseline and checkpoints remain preserved in Drive,
- rerun Notebook 6 section 12 after Drive access succeeds; inspect its class
  coverage before adding loss weighting or launching another T4 run.

## Run 2026-07-13 - CPU Label-Distribution Audits

Status: completed preprocessing audits; no CPU model training performed.

Runtime and recovery:

- Colab GPU access remained unavailable because of usage limits,
- a Python 3 CPU runtime was selected explicitly,
- Google Drive mounting failed again after 120 seconds,
- the official archive was downloaded to temporary Colab storage instead,
- archive SHA-256 matched the recorded value
  `2b4bf0b2357ba982fe6d81da55841874afdd721a867bb8fddede9e04e4914027`,
- all 8,345 RGB tiles were extracted successfully.

Seeded 256/256 development audit:

- records: 512,
- valid pixels: 117,914,492,
- background fraction: `0.7438144414004684`,
- drydown fraction: `0.18750074418333584`,
- nutrient deficiency, storm damage, and waterway had zero positive pixels.

Complete train/validation audit:

- records: 6,553 (4,505 train and 2,048 validation),
- valid pixels: 1,506,195,922,
- nutrient deficiency and waterway had zero positive pixels,
- storm damage fraction: `1.2925277326570798e-05`.

Train-only audit for loss design:

- records: 4,505,
- valid pixels: 1,027,983,041,
- background fraction: `0.7620465102595014`,
- drydown fraction: `0.16986311158415307`,
- weed-cluster fraction: `0.043641380461256075`,
- storm-damage fraction: `1.8938055613312397e-05`,
- nutrient deficiency and waterway: zero positive pixels.

Interpretation:

- subset ordering was not the sole cause of background dominance,
- two configured channels are absent from the complete train/validation data
  and cannot be learned in this experiment,
- class weighting must use train-only counts and exclude absent channels,
- CPU is suitable for these audits; training speed must be measured separately
  before using CPU for optimization runs.

## Run 2026-07-13 - Controlled CPU Training Comparison

Status: completed validation-only development comparison; not a final benchmark.

Runtime and configuration:

- Google Colab Python 3 CPU runtime,
- Agriculture-Vision 2017 miniscale data in temporary Colab storage,
- the same sorted-prefix 64-train/64-validation selection used by the initial
  development baseline,
- three epochs, batch size 4, learning rate `0.001`, U-Net base channels 16,
  and random seed 17,
- test labels were not loaded.

CPU timing checks:

- an 8-train/8-validation, one-epoch, base-channel-4 weighted smoke run took
  `14.099980399999822` seconds,
- the same smoke run with base channels 16 took `19.270197500999984` seconds,
- the 64/64 unweighted three-epoch run took `430.3362569859996` seconds,
- the matched train-pixel-weighted run took `459.02466035199996` seconds.

Comparison:

- unweighted best validation modified mIoU: `0.09445727757198079`,
- weight-cap-20 best validation modified mIoU: `0.02358394564401981`,
- the weighted run excluded the train-absent `nutrient_deficiency` and
  `waterway` channels from its objective,
- the weighted run improved its own modified mIoU over its three epochs, but
  did not outperform the matched unweighted run.

Interpretation:

- CPU training is technically valid and is practical for small controlled
  development comparisons,
- T4 remains preferable for larger subsets and longer sweeps because even this
  64/64 pair required about 14.8 minutes in total,
- simple capped negative-to-positive pixel weighting is not adopted: it harmed
  the selected validation metric in this comparison,
- the unfavorable result is preserved rather than discarded,
- the exact summary and artifact hashes are in
  `outputs/evaluations/week6_segmentation_cpu_compare64_summary.json`.

## Run 2026-07-14 - Imbalance-Aware T4 Comparison

Status: completed validation-only development comparison; not a final
benchmark.

Runtime and configuration:

- Google Colab NVIDIA T4 runtime,
- Agriculture-Vision 2017 miniscale data,
- the same sorted-prefix 64-train/64-validation development selection,
- three epochs, batch size 4, learning rate `0.001`, U-Net base channels 16,
  and random seed 17,
- positive class weights derived only from the complete train-label audit and
  capped at 20,
- train-absent `nutrient_deficiency` and `waterway` channels excluded from the
  weighted objective,
- test labels were not loaded,
- checkpoints and full metrics saved in the private Google Drive experiment
  directory, not committed to GitHub.

Result:

- epoch validation modified mIoU: `0.0`, `0.011110586335664899`,
  `0.03748389352181541`,
- best validation modified mIoU: `0.03748389352181541`,
- prior T4 unweighted development baseline: `0.09651361447267072`,
- matched CPU unweighted development baseline: `0.09445727757198079`,
- matched CPU weight-cap-20 result: `0.02358394564401981`.

Interpretation:

- the weighted T4 run learned across its three epochs and exceeded the matched
  CPU weighted result,
- it did not outperform either unweighted development baseline,
- capped negative-to-positive pixel weighting remains a preserved negative
  result and is not adopted as the next model configuration,
- these are validation-only development results and must not be presented as
  final Agriculture-Vision benchmark performance,
- the tracked result summary is
  `outputs/evaluations/week6_segmentation_t4_weightcap20_summary.json`.

## Run 2026-07-14 - Fixed Seed-17 256/256 T4 Baseline

Status: completed validation-only development comparison; not a final
benchmark.

Protocol and configuration:

- preregistered in `docs/week6_fixed_holdout_protocol.md`,
- Google Colab NVIDIA T4 runtime,
- deterministic SHA-256-ranked Agriculture-Vision subset with seed 17,
- 256 official training records and 256 held-out official validation records,
- five epochs, batch size 4, learning rate `0.001`, U-Net base channels 16,
  and random seed 17,
- unweighted binary cross-entropy,
- the manifest contained 256 test references, but test labels were not loaded,
- checkpoints and complete metrics saved in private Google Drive.

Result:

- epoch validation modified mIoU: `0.04295363769610412`,
  `0.07348724998159521`, `0.07345180489710658`,
  `0.09257792955527273`, `0.0925782719754147`,
- best validation modified mIoU: `0.0925782719754147`,
- prior unweighted 64/64 T4 result: `0.09651361447267072`,
- absolute difference from the prior result: `-0.00393534249725602`,
- final background IoU: `0.7406261758033176`,
- final IoU for every evaluated anomaly class: `0.0`,
- `nutrient_deficiency` and `waterway` had no validation positives and their
  IoUs were undefined.

Interpretation:

- training and validation losses decreased across all five epochs,
- scaling the same small unweighted U-Net configuration did not improve the
  selected metric,
- the modified mIoU remained dominated by background, so numerical convergence
  did not produce useful anomaly segmentation,
- scale alone is not adopted as the next improvement,
- the tracked result and artifact hashes are in
  `outputs/evaluations/week6_segmentation_seed17_dev256_t4_summary.json`.

## Run 2026-07-14 - Fixed 256/256 BCE-Dice T4 Comparison

Status: completed validation-only development comparison; not a final
benchmark.

Controlled change:

- retained the fixed seed-17 256-train/256-validation subset, small U-Net,
  optimizer, learning rate, batch size, five epochs, and evaluation metric,
- replaced the BCE-only objective with unweighted masked BCE plus anomaly-only
  soft Dice at weight `1.0`,
- excluded background and train-absent classes from the Dice term,
- used only the complete train-label audit to determine active Dice classes,
- loaded no test labels.

Verification:

- Colab/T4 PyTorch objective and CLI tests: 8 passed,
- all five epochs completed,
- metrics, training configuration, best checkpoint, and last checkpoint were
  preserved in private Google Drive and hashed.

Result:

- epoch validation modified mIoU: `0.041749587399769264`,
  `0.08292709386185898`, `0.09194819946870963`,
  `0.11316651470693569`, `0.15387379872696982`,
- best validation modified mIoU: `0.15387379872696982`,
- matched BCE result: `0.0925782719754147`,
- absolute improvement: `0.06129552675155513`,
- relative improvement: approximately `66.2%`,
- final background IoU: `0.7492113357703707`,
- final drydown IoU: `0.327905255318418`,
- all other evaluated anomaly-class IoUs remained `0.0`.

Interpretation:

- this is the first fixed-subset objective comparison to improve the aggregate
  metric and produce nonzero IoU for an anomaly class,
- the result is still narrow and does not establish useful segmentation across
  the remaining anomaly classes,
- BCE-Dice becomes the leading development objective for the next controlled
  experiment, not a final model or benchmark claim,
- exact settings and artifact hashes are recorded in
  `outputs/evaluations/week6_segmentation_seed17_dev256_bce_dice_t4_summary.json`.
