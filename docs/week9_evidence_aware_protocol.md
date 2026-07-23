# Week 9 Evidence-Aware Decision Protocol

## Purpose

This protocol evaluates whether Shepherd-AI distinguishes missions that may
proceed from missions that require operator clarification or deterministic
blocking. It does not replace the roadmap metrics or hide the negative Week 8
vision result.

The candidate paper contribution is narrower than a claim that Shepherd-AI is
the first system to validate plans or ask questions. Prior systems already use
structured tools, safety filters, feedback, verification, and in some cases
clarification. The experiment instead measures operator-facing evidence
decisions across Shepherd-AI's modular language, grounding, planning,
scheduling, and safety boundaries.

## Research Questions

1. On registered cases, how accurately does the evidence-aware pipeline choose
   among `proceed`, `clarify`, and `block`?
2. How often does removing map, fleet, policy, and intermediate-evidence checks
   cause a command-only system to proceed silently when it should not?
3. When a registered valid clarification is supplied, how often does the
   dialogue or conflict-resolution path recover?

## Systems

### Shepherd Evidence-Aware v1

The implemented modular pipeline:

- returns `clarify` for ambiguous, unresolved, or conflicting grounded
  references;
- returns `block` for scheduling or configured safety failures; and
- returns `proceed` only when the current bounded stage has enough evidence to
  advance.

For Week 8 preparation, `proceed` means advance to required evidence
acquisition. It does not mean the mission has executed or succeeded.

### Single-Pass Actionability Baseline v1

The baseline sees only command text and proceeds whenever the existing parser
identifies an action. It has no map, fleet state, safety policy, or
intermediate evidence.

This baseline is a no-evidence-gate ablation. It is not TACOS, not a
reimplementation of the TACOS monolithic ablation, and not an LLM result. A
strong monolithic LLM comparison remains unevaluated.

## Registered Data

| Stratum | Records | Provenance | Role |
| --- | ---: | --- | --- |
| Grounding sufficiency | 22 | Existing human-written Week 3 holdout commands | Proceed versus clarify |
| Preflight evidence | 12 | Existing synthetic Week 7 development cases | Proceed, clarify, or block |
| Conflicting references | 4 | Synthetic controlled Week 9 cases | Conflict detection and one valid resolution |
| Clarification dialogue | 4 | Existing synthetic Week 7 stateful cases | Confirmation, retry, cancellation, and timeout |

The pooled decision result contains 38 cases. The strata are also reported
separately because their provenance and task definitions differ.

## Metrics

- Decision accuracy: exact `proceed`/`clarify`/`block` matches.
- False-refusal rate: non-`proceed` predictions divided by gold `proceed`
  cases.
- Silent-misexecution proxy rate: `proceed` predictions divided by gold
  `clarify` or `block` cases. This is a decision-level proxy; the benchmark
  does not execute the incorrectly advanced missions.
- Clarification recall: correct `clarify` predictions divided by gold
  clarification cases.
- Block recall: correct `block` predictions divided by gold blocking cases.
- Clarification-recovery rate: successful resolutions divided by registered
  valid recovery attempts.

Every metric stores its numerator and denominator. A metric with no applicable
cases is `null`, not zero.

## Reproduction

```powershell
python scripts/evaluate_evidence_aware_decisions.py
python -m pytest tests/test_evidence_evaluation.py tests/test_evaluate_evidence_aware_decisions_cli.py -q
```

Raw and derived artifacts:

- `outputs/evaluations/week9_evidence_aware_decisions_v1.json`
- `reports/week9_evidence_aware_decisions_v1.md`

The JSON records input paths, SHA-256 hashes, Python version, strategy,
per-case predictions, metric denominators, and claim limits.

## Interpretation Limits

- Safety, conflict, and dialogue cases are synthetic development diagnostics.
- The mechanisms and most synthetic cases existed before this paper
  evaluation, so the pooled result is not an unseen-system benchmark.
- The 22 grounding commands are human-written, but they do not constitute a
  representative user study.
- The command-only baseline intentionally lacks evidence and is therefore a
  mechanism ablation, not a strong monolithic planner.
- No result establishes physical safety, open-world reliability, or a
  state-of-the-art claim.
