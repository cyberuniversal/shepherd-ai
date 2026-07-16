# Reports

Use this directory for research notes, generated tables, figures, and manuscript drafts.

Git policy: generated reports and worksheets are ignored by default. Commit only
this README unless a specific report is intentionally promoted with `git add -f`
and documented in the commit message.

Every reported result must trace to:

- source data,
- code or notebook used,
- model/configuration,
- random seed when applicable,
- raw output under `outputs/`.

Current generated reports:

- `week2_status_summary.md`: compact Week 2 status report generated from raw ASR, intent, span, span-to-intent, and Colab/T4 token-classifier artifacts. Regenerate it with `scripts/summarize_week2_status.py`.
- `week2_performance_risk_audit.md`: claim-strength audit explaining why current Week 2 metrics can be high. Regenerate it with `scripts/audit_week2_performance_risks.py`.
- `week2_audio_generalization_packet.md`: blank pre-registration worksheet for collecting a future non-overlapping audio validation/test batch. Regenerate it with `scripts/create_week2_audio_generalization_packet.py`.
- `week2_audio_generalization_asr_report.md`: report for the completed 30-record non-overlapping local-GPU Whisper ASR run.
- `week2_audio_generalization_intent_review_packet.md`: draft intent-label review packet for the 30-record audio generalization batch. Regenerate it with `scripts/create_week2_audio_intent_review_packet.py`.
- `week2_audio_v3_holdout_packet.md`: blank pre-registration worksheet for the next non-overlapping audio validation/test batch after the post-hoc `deterministic_v3` parser update. It contains no collected data or evaluation result.
- `week2_span_intent_assembly_report.md`: analysis of whether Colab/T4 token-classifier span predictions assemble into the roadmap intent JSON fields.
- `week2_transformer_transcript_intent_report.md`: evaluation of the imported Colab/T4 token classifier on the 30-record `audio_v2_holdout` transcript intent benchmark, with human-transcript and ASR-transcript results kept separate.
- `week2_transformer_transcript_intent_error_analysis.md`: failure analysis separating clean-transcript transformer intent errors from ASR-added errors on the same 30-record benchmark.
- `week2_audio_v2_span_remediation_packet.md`: human span-labeling worksheet for the `audio_v2_holdout` clean-transcript failures. It contains blank spans and must not be treated as gold data until reviewed.
- `week2_to_week3_nlp_handoff.md`: explicit Week 2 NLP handoff contract for Week 3 grounding, including the provisional parser decision, evidence, caveats, and grounding validation requirements.
- `week2_post_development_audio_packet.md`: blank packet for collecting the fresh non-overlapping post-development Week 2 audio benchmark.
- `week2_completion_gate_audit.md`: generated Week 2 completion-gate audit. It should block advancement until the fresh post-development benchmark exists.
- `week3_completion_gate_audit.md`: generated Week 3 completion-gate audit separating synthetic-map readiness from real-world grounding claims.
- `week3_human_grounding_packet.md`: human-written Week 3 grounding benchmark packet corresponding to `datasets/maps/human_grounding_benchmark_v1.jsonl`.
- `week4_mission_planning_report.md`: summary of the initial deterministic Week 4 task-sequence planner and its planning-gate evaluation.
- `week5_schedule_comparison_v1.md`: generated Week 5 deterministic scheduling strategy comparison and primary assignment table.
- `week5_completion_gate_audit.md`: generated Week 5 completion-gate audit separating roadmap deliverables from deferred research claims.
- `week7_safety_development_v1.md`: preflight safety branch evaluation.
- `week7_clarification_development_v1.md`: stateful dialogue evaluation.
- `week7_route_safety_development_v1.md`: straight-line route geometry evaluation.
- `week7_supervision_development_v1.md`: event-driven lifecycle and telemetry evaluation.
- `week7_integration_development_v1.md`: prior-module interface integration evaluation.
- `week7_policy_sensitivity_v1.md`: synthetic threshold sensitivity analysis.
- `week7_completion_gate_audit.md`: corrected Week 7 completion audit; it supersedes the earlier preflight-only completion claim.
