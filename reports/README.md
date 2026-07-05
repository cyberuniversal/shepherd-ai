# Reports

Use this directory for research notes, generated tables, figures, and manuscript drafts.

Every reported result must trace to:

- source data,
- code or notebook used,
- model/configuration,
- random seed when applicable,
- raw output under `outputs/`.

Current generated reports:

- `week2_status_summary.md`: compact Week 2 status report generated from raw ASR, intent, span, and Colab/T4 token-classifier artifacts. Regenerate it with `scripts/summarize_week2_status.py`.
- `week2_performance_risk_audit.md`: claim-strength audit explaining why current Week 2 metrics can be high. Regenerate it with `scripts/audit_week2_performance_risks.py`.
