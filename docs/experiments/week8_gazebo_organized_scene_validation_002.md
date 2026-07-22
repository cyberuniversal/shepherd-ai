# Week 8 Organized Gazebo Scene Validation 002

## Purpose

Validate the active organized Shepherd site after applying the scene-layout
lesson from the TACOS literature entry without adopting TACOS's known-world,
fixed-altitude, perfect-tracking, or no-perception assumptions.

## Configuration

- Date: 2026-07-18
- World profile: `organized_shepherd_site_v2`
- World SHA-256: `27dce6cd9fdf300953c6d719fc8badb518f540f023cb0af0d0c160dbe43442d0`
- Gazebo Sim: 8.11.0
- ROS distribution: Jazzy
- GPU: NVIDIA GeForce GTX 1650 SUPER
- Model: generic COCO YOLOv8n engine-test checkpoint
- RGB sensor rate: 5 Hz
- Inference persistence interval: 2 wall-clock seconds
- Semantic sensor: dormant; no evaluation subscriber
- Run duration: 60 wall-clock seconds

## Stored Result

Raw and analyzed outputs are under
`outputs/gazebo/organized_scene_validation_002/`.

- 21 unique, checksum-valid RGB frames
- 21 completed inference events and zero failed events
- 54 controller telemetry records
- 186.36 m telemetry path length
- One reached takeoff waypoint
- Zero stored detections
- Route incomplete because the run was time-bounded
- All ROS and Gazebo worker processes terminated after shutdown

A diagnostic sample during the run reported a Gazebo real-time factor of
0.998. At a separate instantaneous GPU diagnostic, utilization was 18%, memory
use was 1118 MiB of 4096 MiB, and temperature was 36 C. These are single
diagnostic observations, not benchmark distributions or acceptance thresholds.

## Visual Check

Stored frame `week8_gazebo_search_frame_000021_stamp_50_200000000.jpg` shows
the route crossing visually distinct field soil, crop geometry, a connector
road, and the surrounding ground surface. This establishes that the new scene
geometry enters the drone RGB stream; it does not establish detector quality.

## Limits

This run does not use the frozen Week 6 checkpoint, complete the route, evaluate
semantic labels, execute three drones, or establish mission success. GUI
smoothness remains dependent on WSLg and the host desktop compositor. A
view-only launch mode is available for inspecting scene organization without
the YOLO worker, but it is not a perception experiment.
