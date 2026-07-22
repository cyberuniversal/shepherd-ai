# Week 8 Gazebo Profile Split Validation 005

## Purpose

Verify that the organized Gazebo scene has a lightweight inspection profile
without weakening the separate RGB-perception experiment profile.

## Configuration

- Date: 2026-07-18
- World profile: `organized_shepherd_site_v2`
- World SHA-256: `27dce6cd9fdf300953c6d719fc8badb518f540f023cb0af0d0c160dbe43442d0`
- Gazebo Sim: 8.11.0
- ROS distribution: Jazzy
- GPU: NVIDIA GeForce GTX 1650 SUPER
- Perception interpreter: `/opt/shepherd-ai-venv/bin/python`
- Model: generic COCO YOLOv8n engine-test checkpoint
- Model SHA-256: `f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36`

## View-Only Result

The 20-second run is stored under
`outputs/gazebo/minimal_gui_validation_002/`.

- The custom Shepherd GUI loaded successfully.
- Only the command and odometry bridge was created.
- No RGB or camera-info bridge was created.
- No YOLO process or RGB evidence manifest was created, as intended.
- The controller loaded the 13 target-free East Field search waypoints.
- No Gazebo, bridge, controller, or inference worker remained after shutdown.

This is an environment-inspection result, not a perception experiment.

## Perception Result

The 35-second bounded run is stored under
`outputs/gazebo/organized_scene_perception_validation_005/`.

- 10 unique, checksum-valid RGB frames were stored.
- 10 inference events completed on `cuda:0`; none failed.
- 29 controller telemetry records were stored.
- Telemetry path length was 78.51 m.
- One waypoint was reached; the time-bounded route was incomplete.
- Generic COCO YOLOv8n produced zero detections.
- Runtime metadata records Python 3.12.3, torch 2.13.0+cu130,
  Ultralytics 8.4.92, the world hash, model hash, and resolved GPU device.

These results establish that the optimized normal profile still renders,
persists, and infers on RGB frames. They do not establish detection quality,
target localization, route completion, or mission success.

## Preserved Failed Attempts

`organized_scene_perception_validation_003` failed before inference because
the ROS-generated console script used `/usr/bin/python3`, where Ultralytics was
not installed. The launch contract now prefixes the perception node with the
documented virtual-environment interpreter.

`organized_scene_perception_validation_004` failed in preflight because a
Windows-to-WSL quoting error reduced the dependency check to an invalid Python
statement. The corrected preflight sources ROS, sets the Ultralytics config
directory, and imports `rclpy`, `torch`, and `ultralytics` before Gazebo starts.

The successful timed run emitted a ROS odometry-conversion exception during
SIGINT teardown after artifacts had been flushed. This was not observed during
the view-only validation and is retained as an unresolved shutdown race rather
than being treated as a clean process-exit result.
