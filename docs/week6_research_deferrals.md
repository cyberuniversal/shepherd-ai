# Week 6 Research Deferrals

The current Week 6 work is a vision-inference foundation, not a completed
computer-vision benchmark.

Agriculture-Vision CVPR 2020 is selected, its terms were accepted for a Colab
run, and a real 30-image subset was processed. The following remain deferred:

- label-schema mapping,
- semantic-segmentation model training,
- dataset-backed modified mIoU evaluation using the official overlapping masks
  (the metric implementation now exists, but has not been run on those labels),
- comparison across YOLO model sizes or other detectors,
- integration of detections into mission reports,
- safety use of detections.

The roadmap names public imagery families such as VisDrone, UAVDT, DOTA, xView,
and Agriculture-Vision. Do not report generic YOLO output as Agriculture-Vision
segmentation performance. The prior download existed only in an expired Colab
runtime and must be reproduced before label mapping or training.
