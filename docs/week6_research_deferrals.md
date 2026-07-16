# Week 6 Research Deferrals

Week 6 is complete for roadmap advancement, but neither vision task is a final
computer-vision benchmark.

Completed evidence:

- Agriculture-Vision label mapping, compact U-Net training, and modified-mIoU
  development comparisons on fixed and stratified 256/256 subsets,
- a leading fixed-subset BCE-Dice modified mIoU of `0.15387`, with drydown as
  the only anomaly class with nonzero IoU,
- a registered 50-epoch VisDrone2019-DET YOLOv8n baseline with validation
  mAP50-95 `0.16724`,
- tracked configurations, split definitions, seeds, versions, metrics, and
  private-artifact hashes.

The following remain deferred:

- final Agriculture-Vision test-set evaluation,
- broader nonzero Agriculture-Vision anomaly-class coverage,
- comparison across YOLO model sizes or other detectors,
- mission-specific ingestion of vision outputs,
- evaluation of whether detections improve mission outcomes or safety.

Do not report the Agriculture-Vision YOLO smoke test as segmentation
performance, the development U-Net as a final benchmark, or the VisDrone result
as mission performance. See `docs/week6_completion_assessment.md`.
