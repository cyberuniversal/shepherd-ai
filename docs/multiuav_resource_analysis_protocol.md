# MultiUAV Resource Analysis Record

## Status

The registered secondary resource analysis is complete. This document records
the analysis boundary, outputs, and limitations after the complete attempt-3
campaign passed score-blind admission. It does not modify the hash-bound study
or hardware protocols.

The analysis specification was frozen at
`2026-08-11T05:29:33.2437798Z`, after campaign execution and score-blind
admission but before any resource aggregate or paired method comparison was
inspected. It is therefore a post-execution binding of analysis decisions that
were already stated in the code plan, validation-study protocol, hardware
protocol, and accuracy protocol. It is not represented as a preregistration.

## Integrity Boundary

The analysis requires:

- the admitted 24-condition, 3,600-row attempt-3 archive;
- the exact score-blind admission SHA-256;
- the frozen 450-row resource schedule;
- the frozen accuracy, hardware, study, and code-plan source hashes;
- three repetitions reported separately;
- no hidden-label access or model invocation; and
- an explicit allowlist that projects raw rows immediately to identifiers and
  numeric resource measurements.

The safe derived schema excludes prompts, requests, messages, responses, raw
model output, parsed plans, evidence ledgers, and hidden references. The
persisted derived-row and bootstrap archives contain no exact forbidden output
keys.

## Registered Analysis

For every repetition, model, method, source-task cluster, and metric, the first
aggregate is the arithmetic mean across the cluster's five dependent variants.
The 30 cluster means are summarized with their mean, median, sample standard
deviation, minimum, and maximum.

The eight secondary resource outcomes are:

- complete method-case duration;
- input tokens;
- output tokens;
- model-call count;
- process RAM peak;
- board VRAM peak;
- process VRAM peak; and
- NVIDIA GPU-board energy.

GPU-utilization peak and temperature peak are diagnostics only. Registered
paired analyses cover M3 minus M1 and M3 minus M4 for the eight secondary
outcomes. Each model and repetition is analyzed separately using 10,000
fixed-seed source-cluster bootstrap draws and a 95% percentile interval. No
null-hypothesis tests or pooled repetition estimate are used. Resource
inference is secondary and exploratory.

## Completed Outputs

- Analysis summary:
  `outputs/evaluations/multiuav_resource_analysis_v1/summary.json`
- Safe derived metric rows:
  `outputs/evaluations/multiuav_resource_analysis_v1/derived_resource_rows.zip`
- Cluster summaries and raw bootstrap draws:
  `outputs/evaluations/multiuav_resource_analysis_v1/bootstrap_evidence.zip`
- Descriptive source table:
  `outputs/tables/multiuav_resource_descriptive_v1.csv`
- Paired-contrast source table:
  `outputs/tables/multiuav_resource_contrasts_v1.csv`
- Bounded results report: `reports/multiuav_resource_results_v1.md`
- M3-minus-M1 and M3-minus-M4 figures under `reports/figures/`
- Reporting manifest:
  `outputs/evaluations/multiuav_resource_reporting_v1/manifest.json`

The production analysis contains 3,600 safe metric rows, 240 descriptive
summaries, and 96 registered paired analyses. An independent rerun produced
byte-identical derived-row and bootstrap-evidence archives.

## Protocol Deviation

Before the analysis specification was frozen, a diagnostic schema-inspection
command printed one admitted row's nested request and raw output. The campaign
and score-blind admission were already immutable. The command exposed no
resource aggregate, paired method comparison, or hidden label. The event and
its timing are preserved in
`datasets/multiuav_plat/resource_analysis_protocol_deviation_v1.json` and must
be disclosed in the manuscript. It does not invalidate the completed
measurements, but a claim that no post-admission human raw-output inspection
occurred would be false.

## Claim Limits

- Resource findings are secondary and exploratory.
- GPU-board energy is not workstation, simulator, network, or UAV energy.
- Peak memory is an absolute observed maximum, not a baseline-subtracted
  allocation.
- The measurements are specific to one locked RTX 3090 campaign.
- M4 is matched to M3 only by model-call count.
- The experiment compares system configurations; it does not isolate a single
  causal mechanism or establish generality beyond the two frozen Qwen scales.

## Reproduction

```powershell
python scripts/analyze_multiuav_resources.py
python scripts/build_multiuav_resource_report.py
```

The next gate is manuscript integration and a final traceability/completion
audit across accuracy and resource evidence.
