# Week 6 Dataset Decision

## Decision

Use the Agriculture-Vision CVPR 2020 dataset as the first Week 6 aerial-imagery
source. This decision is limited to non-commercial research use under the
dataset's own terms.

Official sources checked on 2026-07-11:

- Registry: <https://registry.opendata.aws/intelinair_agriculture_vision/>
- Maintainer repository: <https://github.com/SHI-Labs/Agriculture-Vision>
- Terms: <https://intelinair-data-releases.s3.amazonaws.com/agriculture-vision/cvpr_paper_2020/Agriculture-Vision%20Dataset%20Terms%20of%20Use.pdf>
- Paper: <https://openaccess.thecvf.com/content_CVPR_2020/html/Chiu_Agriculture-Vision_A_Large_Aerial_Image_Database_for_Agricultural_Pattern_Analysis_CVPR_2020_paper.html>

## Why This Dataset

- The roadmap explicitly lists Agriculture-Vision for agricultural inspection.
- The official AWS registry exposes the data without requiring an AWS account.
- The official source documents the train/validation/test split and states that
  crops from the same farmland do not cross splits.
- The source provides explicit terms instead of leaving the license unstated.
- Its RGB aerial farmland images match Shepherd-AI's crop-inspection scenario.

## Terms And Source-Control Constraints

The terms grant a limited, revocable license for non-commercial research and
prohibit redistribution. Downloading signifies agreement. Shepherd-AI therefore:

- never accepts the terms automatically,
- requires an explicit `--accept-terms` flag during manifest preparation,
- does not commit raw Agriculture-Vision images or derived image datasets,
- records the official provenance URL, terms URL, license description, split,
  and SHA-256 digest for every selected input image.

The user must personally review and accept the official terms before download.

## Task And Model Compatibility

Agriculture-Vision is a semantic-segmentation dataset. Its labels are overlapping
agricultural anomaly masks over RGB and NIR imagery. The official challenge uses
a modified mean intersection-over-union metric.

The roadmap separately asks for Ultralytics YOLO. A generic COCO-pretrained YOLO
model does not predict Agriculture-Vision anomaly masks. The first YOLO run is
therefore a pipeline smoke test only:

- valid evidence: model executed on real aerial images, raw detections and
  confidence values were saved, and annotated images were generated;
- invalid claims: Agriculture-Vision mIoU, anomaly-detection performance,
  mission success, crop-health accuracy, or detector generalization.

A research-valid Agriculture-Vision experiment requires a segmentation model,
the official masks, the official split policy, and modified mIoU evaluation.
The overlap-aware metric implementation now exists and is unit tested, but the
2017 archive label mapping, model training, and dataset-backed evaluation are
not implemented yet.

## Initial Experiment

1. Download one official year archive in Colab after explicit terms acceptance.
2. Preserve the source split and select at most 10 RGB images per split in
   deterministic path order.
3. Build `datasets/aerial_images/manifest.jsonl` with SHA-256 digests.
4. Validate the manifest.
5. Run a small Ultralytics YOLO model as a smoke-test baseline.
6. Save raw detections separately from summaries and annotated images.
7. Preserve zero-detection and failed runs as negative results.

Successful completion of this initial experiment means reproducible execution,
not positive detection quality.
