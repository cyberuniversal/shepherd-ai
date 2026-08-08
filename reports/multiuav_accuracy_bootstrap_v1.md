# MultiUAV Accuracy Bootstrap Report

## Status

The frozen 3B and 7B accuracy matrices were structurally admitted, scored under
the registered label-separated contract, and analyzed with the preregistered
source-task-cluster bootstrap. This report covers accuracy outcomes only. It
does not include the pending resource experiment or live mission execution.

## Registered Analysis

- Resampling unit: source-task cluster
- Source clusters per model: 284
- Variants per cluster: 2 for unsafe proceed and 5 for end-to-end success
- Bootstrap draws: 10,000
- Seed: `shepherd-multiuav-primary-bootstrap-v1`
- Interval: 95% percentile bootstrap
- Null-hypothesis tests: none
- Primary contrast: M3 stage-wise minus M1 monolithic
- Confirmatory contrast: M3 stage-wise minus M4 compute-matched post-plan

Negative differences favor M3 for unsafe proceed because lower is better.
Positive differences favor M3 for end-to-end success because higher is better.

## Results

| Model | Contrast | Outcome | M3-minus-baseline | 95% cluster-bootstrap interval |
|---|---|---|---:|---:|
| Qwen2.5-3B | M3 - M1 | Unsafe proceed | -0.7905 | [-0.8275, -0.7518] |
| Qwen2.5-3B | M3 - M1 | End-to-end success | 0.0000 | [0.0000, 0.0000] |
| Qwen2.5-3B | M3 - M4 | Unsafe proceed | -0.0018 | [-0.0053, 0.0000] |
| Qwen2.5-3B | M3 - M4 | End-to-end success | 0.0000 | [0.0000, 0.0000] |
| Qwen2.5-7B | M3 - M1 | Unsafe proceed | -0.6831 | [-0.7324, -0.6338] |
| Qwen2.5-7B | M3 - M1 | End-to-end success | 0.1606 | [0.1507, 0.1697] |
| Qwen2.5-7B | M3 - M4 | Unsafe proceed | -0.0264 | [-0.0405, -0.0141] |
| Qwen2.5-7B | M3 - M4 | End-to-end success | 0.1521 | [0.1415, 0.1627] |

## Interpretation

For Qwen2.5-7B, M3 has favorable paired differences on both registered primary
outcomes against M1 and M4, and all four 7B intervals exclude zero. The result
supports a bounded claim that stage-wise evidence validation changed the
safety-utility trade-off under this static benchmark and scoring contract.

The 3B result is weaker. M3 sharply reduces unsafe proceed relative to M1, but
M3, M1, and M4 all achieve zero strict end-to-end success. M3 and M4 are also
nearly indistinguishable on 3B unsafe proceed, with the interval reaching zero.

The 7B result does not establish that the problem is solved. M3's descriptive
end-to-end success rate is 0.1606, meaning most cases still fail the strict
registered contract. The result concerns controlled derivatives, two frozen
Qwen scales, static plan fidelity, and source-task-cluster resampling. It does
not establish real-flight performance, general model-family superiority, or a
complete safety solution.

## Figures

The publication figures are generated from the frozen aggregate summaries,
not from raw model output:

- `reports/figures/multiuav_accuracy_primary_outcomes_v1.png` and `.pdf` show
  the two registered absolute outcome rates for all four methods and both model
  scales.
- `reports/figures/multiuav_accuracy_registered_contrasts_v1.png` and `.pdf`
  show the eight registered M3 paired differences and 95% source-cluster
  bootstrap intervals.

Exact plotted rows are stored in
`outputs/tables/multiuav_accuracy_primary_rates_v1.csv` and
`outputs/tables/multiuav_accuracy_registered_contrasts_v1.csv`. The figure
manifest binds both source summaries, generator code, environment versions,
tables, and figures by SHA-256.

## Artifacts

- Scoring summary:
  `outputs/evaluations/multiuav_accuracy_scoring_v1/summary.json`
- Bootstrap summary:
  `outputs/evaluations/multiuav_accuracy_bootstrap_v1/summary.json`
- Raw draws and cluster summaries:
  `outputs/evaluations/multiuav_accuracy_bootstrap_v1/bootstrap_evidence.zip`
- Bootstrap evidence SHA-256:
  `49568f91712cc0f75a2e326c7f013c56d97004115517b9db7a68fe645fbd61c2`
- Figure provenance manifest:
  `outputs/evaluations/multiuav_accuracy_figures_v1/manifest.json`
