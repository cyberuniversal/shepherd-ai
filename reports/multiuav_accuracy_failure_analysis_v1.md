# MultiUAV Accuracy Session And Failure Analysis

## Scope

This is a post-hoc descriptive analysis of the admitted 3B and 7B accuracy
matrices. It introduces no new hypothesis test, baseline, model call, or
research direction. Fifteen held-out source sessions appear in each method and
model matrix. The machine-readable session rows and failure counts are in
`outputs/tables/multiuav_accuracy_session_statistics_v1.csv` and
`outputs/evaluations/multiuav_accuracy_failure_analysis_v1.json`.

## Session-Level Results

For 3B, M1 had unsafe continuation in every held-out session; its mean
session-level unsafe-proceed rate was 0.7899. M3 contained every non-executable
case in all 15 sessions, while M2 and M4 contained all such cases in 13 and 14
sessions, respectively. Every 3B method had zero strict success in every
session.

For 7B, M1 again had unsafe continuation in every session, with mean
session-level unsafe-proceed rate 0.6829. M3 contained every non-executable case
in all 15 sessions and had at least one strict success in every session, with a
mean session strict-success rate of 0.1605. M4 had unsafe continuation in seven
sessions and at least one strict success in eight; its mean session
strict-success rate was 0.0083.

## Failure Analysis

The strict-success result must not be read as executable mission success.
Across all 852 executable cases per method, **static plan fidelity was zero for
both models and all four methods**. The 7B M3 strict successes were correct
containment outcomes on non-executable cases. No official simulator or server
execution was performed.

The 3B M1 matrix had 368 parse errors, 249 false non-executions among executable
cases, and 449 unsafe continuations among non-executable cases. M3 eliminated
unsafe continuation but had 544 parse errors and false-nonexecution behavior on
all 852 executable cases. M2 and M4 showed the same basic tradeoff: near-total
containment with no recovered static plan fidelity.

The 7B M1 matrix had 429 parse errors, 267 false non-executions, and 388 unsafe
continuations. M3 reduced parse errors to 273 and eliminated unsafe continuation,
but still failed static plan fidelity on all executable cases. M4 had 392 parse
errors, 850 false non-executions among executable cases, and 15 unsafe
continuations. These counts support a narrow conclusion: validation placement
strongly affected containment, but the completed experiment did not demonstrate
correct executable API plans.

The failure archive contains case, cluster, source-task, and session IDs plus
derived scoring flags. Raw model text remains only in the sealed checkpoints.
