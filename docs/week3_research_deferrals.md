# Week 3 Research Deferrals

## Scope

This document records Week 3 research items that are explicitly deferred rather than silently treated as complete.

## Deferred Items

### Real Or Public Map Provenance

Status: deferred for Week 3.

Reason: the roadmap defines Shepherd-AI as a software simulation and Week 3 as command grounding over a custom CSV or GeoJSON map dataset. The current Week 3 objective is therefore to make map grounding explicit, validated, reproducible, and inspectable over a custom synthetic map before planning begins.

Current implementation status:

- implemented: custom synthetic CSV map,
- implemented: custom synthetic GeoJSON Point map subset,
- implemented: custom synthetic GeoJSON Polygon region fixture,
- implemented: map validation and coverage auditing,
- not implemented: real map dataset,
- not implemented: public map benchmark,
- not evaluated: real-world grounding accuracy.

Condition for revisiting: before claiming real-world grounding performance, external validity, or deployment relevance, Shepherd-AI must add real or public map provenance, licensing/access notes, and separate evaluation.

## Active Non-Deferred Blockers

The following item is not deferred by this document:

- human-collected Week 3 grounding benchmark.

