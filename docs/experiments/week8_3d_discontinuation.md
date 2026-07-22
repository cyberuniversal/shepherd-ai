# Week 8 3D Experiment Discontinuation

## Decision

On 2026-07-21, the operator discontinued both the Three.js telemetry viewer and
the Gazebo/ROS 2 simulation direction. Shepherd-AI returned to the roadmap's
Python software-simulation scope using deterministic telemetry and Folium.

## Evidence Retention

The earlier Gazebo experiment reports remain in `docs/experiments/`, and raw
generated outputs remain locally under `outputs/gazebo/` according to the
repository output policy. They document implementation attempts, failures,
generic-COCO inference, and performance observations. They are historical
negative evidence, not active architecture or Week 8 completion evidence.

The discontinued work must not be used to claim:

- completion of the fixed three-drone roadmap scenario;
- mission-assigned vision evaluation;
- performance of the frozen Week 6 checkpoint;
- image-to-world localization;
- physical-flight validity or safety.

## Active Replacement

Week 8 continues through `src/shepherd_ai/week8_pipeline.py`,
`src/shepherd_ai/mission_simulation.py`, `scripts/run_week8_preflight.py`, and
`scripts/run_week8_simulation.py`. Required ASR, mission-image, metric, and
mission-report evidence remains incomplete until real inputs are registered.
