# Week 7 Policy Sensitivity Evaluation

This is a synthetic decision-sensitivity study, not physical safety calibration.

- Dimensions: `4`
- Expected sequence matches: `4`
- Monotonicity checks passed: `4`

| Dimension | Values | Decisions | Monotonic |
| --- | --- | --- | --- |
| minimum_battery_percent | [20.0, 25.0, 30.0] | ['approved', 'approved', 'rejected'] | True |
| maximum_altitude_m | [50.0, 60.0, 70.0] | ['rejected', 'approved', 'approved'] | True |
| route_clearance_margin_m | [0.0, 20.0, 30.0] | ['approved', 'approved', 'rejected'] | True |
| minimum_inter_drone_separation_m | [10.0, 20.0, 30.0] | ['approved', 'rejected', 'rejected'] | True |
