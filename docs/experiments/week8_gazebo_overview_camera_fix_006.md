# Week 8 Gazebo Overview Camera Fix 006

## Problem

The custom Gazebo GUI opened to blue sky instead of the organized Shepherd
site. The world loaded, but the configured overview camera's optical ray did
not reach the ground until approximately 1,241 m from the camera. That framing
was outside the regression test's usable overview range and was consistent
with the observed empty view.

## Change

The GUI and SDF overview pose changed from
`-420 -980 680 0 0.58 1.57` to `-400 -700 450 0 0.65 1.57`. The new optical
ray intersects the ground approximately 744 m away at a point inside the
bounded Shepherd site.

## Validation

- Date: 2026-07-18
- Profile: view-only
- Active world SHA-256:
  `0e2f0205a1a68c388bd6fac5c8cde18996728f1e043f49fa73033ca5fecba956`
- Gazebo's live `/gui/camera/pose` topic reported position
  `(-400, -700, 450)` with the expected configured orientation.
- Gazebo created `/world/shepherd_farm/scene/info`.
- The ROS package rebuilt successfully.
- The bounded validation left no Gazebo, bridge, controller, or inference
  process running after shutdown.
- A regression test checks that the GUI camera ray intersects the mapped site
  within 900 m.

This validates configuration loading and camera geometry. It is not a
perception, detector-performance, route-completion, or mission-success result.
