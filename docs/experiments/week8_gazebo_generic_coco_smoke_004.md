# Week 8 Gazebo Generic COCO Smoke 004

## Purpose

Validate the one-drone Gazebo/ROS runtime boundary, target-free route control,
RGB capture, artifact hashing, and local-GPU Ultralytics inference. This is an
engine smoke test, not the registered Week 6 VisDrone model experiment.

## Runtime

- Date: 2026-07-18
- Host: Windows WSL 2.7.10.0, Ubuntu 24.04, WSL kernel 6.18.33.2
- Engine: Gazebo Sim 8.11.0
- ROS: Jazzy; `ros-jazzy-ros-gz` 1.0.22 and `ros-jazzy-cv-bridge` 4.1.0
- Python: 3.12.3
- PyTorch: 2.13.0+cu130
- Ultralytics: 8.4.92
- Device: NVIDIA GeForce GTX 1650 SUPER through `cuda:0`
- Model: generic Ultralytics COCO `yolov8n.pt`
- Model SHA-256: `f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36`
- Confidence threshold: 0.25
- Random seed: not applicable; inference only
- World snapshot: `simulation/ros2_ws/src/shepherd_gazebo/worlds/shepherd_farm_smoke_v1.sdf`
- World SHA-256: `7522050d183a4f2a991d679b4482bd57b99c73554bd4566b66f19694009e74ce`

## Stored Artifacts

Raw output remains separate from analysis under
`outputs/gazebo/week8_search_generic_coco_smoke_004/` and is ignored by Git by
default because it contains generated image files.

- 68 unique RGB frame manifest records
- 68 frame files with matching SHA-256 checksums
- 68 completed per-frame inference events; zero failed inference events
- 83 controller telemetry records
- One `waypoint_reached` event for the 30 m takeoff waypoint
- One stored detection classified as `person` at 0.2736 confidence
- Zero stored `car` detections

The generated analysis files are `analysis/run_summary.json` and
`analysis/car_perception_evidence.json`.

## Result

The controller moved from approximately `[0.0, 0.0, 0.40]` to
`[-197.40, -204.00, 29.63]` ENU. The telemetry path length was 312.21 m. The
route did not complete because the smoke run was bounded to 90 seconds.

The hatchback is visibly rendered in camera frame
`week8_gazebo_search_frame_000057_stamp_67_000000000.jpg`, but the generic COCO
model did not classify it as `car`. The coordinate-free perception target
therefore correctly remains `awaiting_vision`.

## Interpretation

Established by this run: the engine starts, the drone moves under the
target-free route controller, RGB pixels cross the ROS bridge, frames and
metadata are stored, and Ultralytics inference runs on the local GPU.

Not established: detector performance, target localization, route completion,
three-drone execution, safety integration, mission success, or Week 8
completion. The frozen Week 6 VisDrone checkpoint is still stored only in the
private Google Drive cache described by the Week 6 summary and is not available
locally. Its Gazebo result remains not evaluated.

Runs `001` and `002` preserve interpreter and ROS parameter-type failures.
Run `003` exposed timestamp-based frame-ID collisions. Those failed and partial
runs remain in `outputs/gazebo/` as negative engineering evidence.
