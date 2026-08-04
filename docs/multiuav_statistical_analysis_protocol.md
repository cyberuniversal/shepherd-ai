# MultiUAV Statistical Analysis Protocol

## Scope

The active study requires source-task-cluster bootstrap intervals and paired
method differences. `src/shepherd_ai/multiuav_statistics.py` implements that
analysis contract. `accuracy_protocol_freeze_v1.json` now defines the primary
estimands before study inference; no outcome has been evaluated.

No MultiUAV study score has been analyzed. Current tests use synthetic numeric
fixtures only.

## Analysis Unit

The independent resampling unit is one authentic source-task cluster, not one
derived case. Every accepted cluster must contain the same five variants for
both methods in a contrast. Duplicate method-variant rows, missing variants,
and non-finite metric values are rejected.

For each cluster, the implementation:

1. averages the five variant scores for method A;
2. averages the same five variant scores for method B;
3. computes the paired A-minus-B difference; and
4. bootstraps the mean of those cluster-level paired differences.

This preserves the dependence among five cases derived from one source task.

## Bootstrap Contract

The default contract uses:

- 10,000 draws;
- a fixed string seed;
- source-task clusters sampled with replacement; and
- a percentile confidence interval with 95% coverage.

The return value separates the analysis summary, per-cluster summaries, and raw
bootstrap draws. A future experiment script must write raw draws separately
from final tables while binding both files to the same data, code, seed, and
configuration hashes.

## Frozen Accuracy Decisions

The score-blind protocol registers:

- M3 stage-wise minus M1 monolithic as the primary paired contrast;
- M3 minus compute-matched M4 as the confirmatory paired contrast;
- unsafe proceed rate on CLARIFY/BLOCK cases, minimized;
- end-to-end case success over all five variants, maximized;
- retention of parse and backend errors, with zero end-to-end success;
- 10,000 fixed-seed source-cluster bootstrap draws and 95% percentile
  intervals;
- no null-hypothesis significance tests; and
- exploratory labeling without confirmatory claims for secondary outcomes.

The publication-summary filter is implemented as a fail-closed admission gate in
`src/shepherd_ai/multiuav_publication.py`. It preserves `PARSE_ERROR` rows as
failures while rejecting synthetic fixtures, resource runs, unapproved cases,
and incomplete matrices. Deterministic row scoring and descriptive aggregation
now exist in `src/shepherd_ai/multiuav_scoring.py`. The scorer distinguishes raw
model output from post-gate system disposition, applies external grounding to
all methods, and accesses hidden official commands only after matrix admission.
No study row has been scored. Cluster-bootstrap execution and figure generation
still do not exist.

The existence of analysis code is not evidence that the study data are ready
or that any method performs better.
