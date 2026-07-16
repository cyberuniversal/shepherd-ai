# Week 7 Route Safety Evaluation

This is a synthetic straight-line geometry evaluation, not trajectory optimization.

- Cases: `3`
- Expected decision matches: `3`
- Expected intersection matches: `3`

| Case | Expected | Actual | Intersections |
| --- | --- | --- | --- |
| week7_route_circle_crossing_001 | rejected | rejected | restricted_circle |
| week7_route_circle_clear_001 | approved | approved | none |
| week7_route_polygon_crossing_001 | rejected | rejected | restricted_polygon |
