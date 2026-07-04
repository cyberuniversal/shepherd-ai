# Week 2 Targeted Span Collection Packet

This is a blank worksheet for real human-written commands and human-verified exact span labels.

Do not treat any row as collected data until the `text` and `spans` fields are filled and validated.

## Summary

- Total blank slots: 35
- Recommended train slots: 27
- Recommended validation slots: 8
- Recommended test slots: 0

## How To Use

1. Write one original command for each slot.
2. Label exact spans with `scripts/create_span_record.py` or `scripts/create_span_record_from_command.py`.
3. Keep targeted follow-up records out of the held-out test split.
4. Validate the updated dataset before training.

## Blank Slots

| Slot | Split | Priority Field | What To Collect |
| --- | --- | --- | --- |
| `human_cmd_followup_001` | `train` | `target` | Collect commands where the target follows scan/inspect/search/capture wording. Include object targets and inspection targets that appear near filler words such as for, of, and to. |
| `human_cmd_followup_002` | `train` | `target` | Collect commands where the target follows scan/inspect/search/capture wording. Include object targets and inspection targets that appear near filler words such as for, of, and to. |
| `human_cmd_followup_003` | `train` | `target` | Collect commands where the target follows scan/inspect/search/capture wording. Include object targets and inspection targets that appear near filler words such as for, of, and to. |
| `human_cmd_followup_004` | `validation` | `target` | Collect commands where the target follows scan/inspect/search/capture wording. Include object targets and inspection targets that appear near filler words such as for, of, and to. |
| `human_cmd_followup_005` | `train` | `target` | Collect commands where the target follows scan/inspect/search/capture wording. Include object targets and inspection targets that appear near filler words such as for, of, and to. |
| `human_cmd_followup_006` | `train` | `target` | Collect commands where the target follows scan/inspect/search/capture wording. Include object targets and inspection targets that appear near filler words such as for, of, and to. |
| `human_cmd_followup_007` | `train` | `target` | Collect commands where the target follows scan/inspect/search/capture wording. Include object targets and inspection targets that appear near filler words such as for, of, and to. |
| `human_cmd_followup_008` | `validation` | `target` | Collect commands where the target follows scan/inspect/search/capture wording. Include object targets and inspection targets that appear near filler words such as for, of, and to. |
| `human_cmd_followup_009` | `train` | `target` | Collect commands where the target follows scan/inspect/search/capture wording. Include object targets and inspection targets that appear near filler words such as for, of, and to. |
| `human_cmd_followup_010` | `train` | `target` | Collect commands where the target follows scan/inspect/search/capture wording. Include object targets and inspection targets that appear near filler words such as for, of, and to. |
| `human_cmd_followup_011` | `train` | `target` | Collect commands where the target follows scan/inspect/search/capture wording. Include object targets and inspection targets that appear near filler words such as for, of, and to. |
| `human_cmd_followup_012` | `validation` | `constraint` | Collect commands with explicit restrictions, sequencing, or safety conditions. Label only the full constraint phrase, not surrounding filler unless it is part of the condition. |
| `human_cmd_followup_013` | `train` | `constraint` | Collect commands with explicit restrictions, sequencing, or safety conditions. Label only the full constraint phrase, not surrounding filler unless it is part of the condition. |
| `human_cmd_followup_014` | `train` | `constraint` | Collect commands with explicit restrictions, sequencing, or safety conditions. Label only the full constraint phrase, not surrounding filler unless it is part of the condition. |
| `human_cmd_followup_015` | `train` | `constraint` | Collect commands with explicit restrictions, sequencing, or safety conditions. Label only the full constraint phrase, not surrounding filler unless it is part of the condition. |
| `human_cmd_followup_016` | `validation` | `constraint` | Collect commands with explicit restrictions, sequencing, or safety conditions. Label only the full constraint phrase, not surrounding filler unless it is part of the condition. |
| `human_cmd_followup_017` | `train` | `constraint` | Collect commands with explicit restrictions, sequencing, or safety conditions. Label only the full constraint phrase, not surrounding filler unless it is part of the condition. |
| `human_cmd_followup_018` | `train` | `constraint` | Collect commands with explicit restrictions, sequencing, or safety conditions. Label only the full constraint phrase, not surrounding filler unless it is part of the condition. |
| `human_cmd_followup_019` | `train` | `constraint` | Collect commands with explicit restrictions, sequencing, or safety conditions. Label only the full constraint phrase, not surrounding filler unless it is part of the condition. |
| `human_cmd_followup_020` | `validation` | `constraint` | Collect commands with explicit restrictions, sequencing, or safety conditions. Label only the full constraint phrase, not surrounding filler unless it is part of the condition. |
| `human_cmd_followup_021` | `train` | `constraint` | Collect commands with explicit restrictions, sequencing, or safety conditions. Label only the full constraint phrase, not surrounding filler unless it is part of the condition. |
| `human_cmd_followup_022` | `train` | `count` | Collect commands with numeric counts, written counts, all-drones wording, and drone identifiers. Keep count spans separate from target or drone-name spans. |
| `human_cmd_followup_023` | `train` | `count` | Collect commands with numeric counts, written counts, all-drones wording, and drone identifiers. Keep count spans separate from target or drone-name spans. |
| `human_cmd_followup_024` | `validation` | `count` | Collect commands with numeric counts, written counts, all-drones wording, and drone identifiers. Keep count spans separate from target or drone-name spans. |
| `human_cmd_followup_025` | `train` | `count` | Collect commands with numeric counts, written counts, all-drones wording, and drone identifiers. Keep count spans separate from target or drone-name spans. |
| `human_cmd_followup_026` | `train` | `count` | Collect commands with numeric counts, written counts, all-drones wording, and drone identifiers. Keep count spans separate from target or drone-name spans. |
| `human_cmd_followup_027` | `train` | `count` | Collect commands with numeric counts, written counts, all-drones wording, and drone identifiers. Keep count spans separate from target or drone-name spans. |
| `human_cmd_followup_028` | `validation` | `action` | Collect commands with more than one mission verb. Include dispatch/send/return wording when it changes the action boundary. Verify every action span manually instead of copying parser output. |
| `human_cmd_followup_029` | `train` | `action` | Collect commands with more than one mission verb. Include dispatch/send/return wording when it changes the action boundary. Verify every action span manually instead of copying parser output. |
| `human_cmd_followup_030` | `train` | `action` | Collect commands with more than one mission verb. Include dispatch/send/return wording when it changes the action boundary. Verify every action span manually instead of copying parser output. |
| `human_cmd_followup_031` | `train` | `action` | Collect commands with more than one mission verb. Include dispatch/send/return wording when it changes the action boundary. Verify every action span manually instead of copying parser output. |
| `human_cmd_followup_032` | `validation` | `action` | Collect commands with more than one mission verb. Include dispatch/send/return wording when it changes the action boundary. Verify every action span manually instead of copying parser output. |
| `human_cmd_followup_033` | `train` | `location` | Collect commands where area names can be confused with target names. Include directional terms and named regions, then label only the phrase that grounds the mission location. |
| `human_cmd_followup_034` | `train` | `location` | Collect commands where area names can be confused with target names. Include directional terms and named regions, then label only the phrase that grounds the mission location. |
| `human_cmd_followup_035` | `train` | `location` | Collect commands where area names can be confused with target names. Include directional terms and named regions, then label only the phrase that grounds the mission location. |
