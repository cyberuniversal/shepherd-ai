# MultiUAV-Plat Source Metadata

This directory contains Shepherd-AI metadata for the pinned MultiUAV-Plat
benchmark source and the sealed, unscored accuracy checkpoints. It does not
contain the upstream repository, benchmark ZIP, images, or unpacked raw model
outputs. The checkpoint ZIPs retain raw outputs under the registered
research-integrity protocol and must not be opened for informal inspection.

The pinned source and acquisition procedure are documented in
`docs/multiuav_source_acquisition.md`. Downloaded upstream files belong under
the ignored `external/MultiUAV-Plat/` checkout.

- `source_registry_v1.json` records the immutable source and field policy.
- `source_audit_v1.json` is the preserved raw output of the successful audit.
- `session_split_v1.json` freezes session placement and source-text overlap.
- `task_eligibility_v1.json` records every task inclusion/exclusion decision
  and the selected upstream alias.
- `study_wiring_audit_v1.json` records the active text-first component path,
  completed gates, legacy exclusions, and current blockers.
- `nautilus/qwen25_3b_accuracy_complete_v1/` and
  `nautilus/qwen25_7b_accuracy_complete_v1/` preserve the two complete 5,680-row
  accuracy matrices and their unscored run metadata.
- `accuracy_matrix_admission_v1.json` records score-blind structural admission
  of both matrices. It contains no raw outputs, hidden labels, or scores.
