# Week 6 VisDrone Detection Protocol

## Purpose

The roadmap recommends VisDrone for drone object detection and requires Week 6
to run aerial-image inference, save detections and confidence values, generate
annotated outputs, and produce a detection summary table. Agriculture-Vision
supports the separate agricultural semantic-segmentation question; it does not
provide YOLO bounding-box labels for the roadmap's detection evaluation.

This protocol defines the first labeled, trainable YOLO detection baseline.

## Dataset

- Dataset: VisDrone2019-DET static-image detection subset.
- Official project: <https://github.com/VisDrone/VisDrone-Dataset>.
- Maintainer: AISKYEYE team, Tianjin University.
- Official split sizes: 6,471 train, 548 validation, and 1,610 test-dev images.
- Classes: pedestrian, people, bicycle, car, van, truck, tricycle,
  awning-tricycle, bus, and motor.
- Ultralytics conversion: `VisDrone.yaml` converts the original annotations to
  YOLO bounding-box format and excludes ignored regions.
- Access note: the official repository publishes download links and citation
  instructions but does not state a dataset license in its README. Shepherd-AI
  records that uncertainty, uses the data only for research, and does not
  redistribute images or annotations.

## Baseline Configuration

- Model: Ultralytics `yolov8n.pt`, initialized from published pretrained
  weights and then fine-tuned on VisDrone train.
- Runtime: Google Colab NVIDIA Tesla T4; CUDA device name must contain `T4`.
- Image size: 640.
- Epoch budget: 50.
- Batch size: 16, reduced only if an out-of-memory failure is preserved first.
- Optimizer selection: Ultralytics `auto`, recorded in generated arguments.
- Random seed: 17.
- Deterministic mode: enabled where supported by the installed stack.
- Workers: 2.
- Validation: official VisDrone validation split after every epoch.
- Checkpoints: best, last, and periodic checkpoints in private Google Drive.
- Test-dev: not used for training, early stopping, or model selection.

The epoch budget is a development baseline, not a claim that convergence or
optimality has been reached. Any interruption is resumed from `last.pt` without
changing the registered configuration.

## Metrics And Outputs

Primary development metrics:

- bounding-box mAP50-95,
- mAP50,
- precision,
- recall,
- per-class average precision,
- training and validation losses.

Required outputs:

- `args.yaml`,
- `results.csv`,
- `best.pt` and `last.pt`,
- validation predictions and confidence values,
- annotated validation examples,
- a compact non-image summary with model/package/device versions and artifact
  hashes.

Detection metrics are module-level results. They are not mission success,
tracking performance, safety evidence, or proof of generalization to farmland
anomalies.

## Leakage Controls

- Preserve the official train/validation/test-dev partition.
- Use validation only for development reporting and checkpoint selection.
- Do not tune against test-dev.
- Do not mix Agriculture-Vision images or masks into this detector experiment.
- Record all parameter changes and failed runs.

## Completion Criteria

- Official dataset conversion completes and split counts are verified.
- The T4 device gate passes.
- Fifty epochs complete, or an interruption/failure and resume state are
  preserved.
- Best and last checkpoints and raw epoch metrics are retained.
- Validation detection metrics and per-class results are exported.
- Annotated validation examples and confidence-bearing raw predictions are
  generated without committing dataset pixels.
- The result is compared only with an explicitly recorded baseline.

## Sources

- Shepherd-AI roadmap, Week 6 and Recommended Public Datasets.
- VisDrone official repository and citation:
  <https://github.com/VisDrone/VisDrone-Dataset>.
- Ultralytics VisDrone dataset configuration and conversion documentation:
  <https://docs.ultralytics.com/datasets/detect/visdrone/>.
