# Evidence-Aware Decision Evaluation

This controlled diagnostic combines a human-written grounding stratum with synthetic safety, conflict, and dialogue strata. It is not a real-world reliability estimate.

## Results

| System | Decision accuracy | False refusal rate | Silent-proceed proxy rate | Clarification recall | Block recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Shepherd evidence-aware | 1.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 |
| Single-pass actionability baseline | 0.6842 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |

- Clarification recovery: `3/3` (`1.0000`).
- Dialogue terminal-status accuracy: `1.0000` over `4` synthetic cases.

## Interpretation

The comparison isolates the behavior of explicit evidence gates against a command-only proceed-if-actionable ablation. The baseline has no map, fleet, policy, or intermediate evidence, so this is not a fair substitute for a strong monolithic LLM baseline. It measures the failure mode created by removing evidence checks.

## Claim Limits

- No monolithic LLM or TACOS reimplementation was evaluated.
- Silent misexecution is a decision-level proxy; incorrect missions were not executed.
- Safety, conflict, and dialogue strata are synthetic.
- Dialogue recovery measures deterministic state handling, not usability.
- No physical flight or real-world reliability claim is supported.
