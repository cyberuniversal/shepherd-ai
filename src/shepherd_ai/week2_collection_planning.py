"""Error-driven Week 2 span collection planning."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


SPAN_FIELDS = ("action", "count", "location", "target", "constraint")

FIELD_COLLECTION_GUIDANCE = {
    "action": [
        "Collect commands with more than one mission verb.",
        "Include dispatch/send/return wording when it changes the action boundary.",
        "Verify every action span manually instead of copying parser output.",
    ],
    "count": [
        "Collect commands with numeric counts, written counts, all-drones wording, and drone identifiers.",
        "Keep count spans separate from target or drone-name spans.",
    ],
    "location": [
        "Collect commands where area names can be confused with target names.",
        "Include directional terms and named regions, then label only the phrase that grounds the mission location.",
    ],
    "target": [
        "Collect commands where the target follows scan/inspect/search/capture wording.",
        "Include object targets and inspection targets that appear near filler words such as for, of, and to.",
    ],
    "constraint": [
        "Collect commands with explicit restrictions, sequencing, or safety conditions.",
        "Label only the full constraint phrase, not surrounding filler unless it is part of the condition.",
    ],
}


def build_week2_collection_plan(
    *,
    span_summary: dict[str, Any],
    evaluation_summary: dict[str, Any],
    error_analysis: dict[str, Any],
    source_paths: dict[str, str],
) -> dict[str, Any]:
    """Build a targeted human collection plan from reviewed model errors.

    The plan intentionally contains collection requirements, not generated
    command text. New command text must still come from a human writer or be
    labeled as synthetic/model-generated data.
    """

    false_negative_counts = _int_counts(error_analysis.get("false_negative_entity_counts", {}))
    false_positive_counts = _int_counts(error_analysis.get("false_positive_entity_counts", {}))
    span_field_counts = _int_counts(span_summary.get("span_field_counts", {}))
    field_priorities = []
    for field in SPAN_FIELDS:
        false_negatives = false_negative_counts.get(field, 0)
        false_positives = false_positive_counts.get(field, 0)
        total_errors = false_negatives + false_positives
        requested_records = _requested_record_count(total_errors)
        field_priorities.append(
            {
                "field": field,
                "false_negative_entities": false_negatives,
                "false_positive_entities": false_positives,
                "total_entity_errors": total_errors,
                "current_span_count": span_field_counts.get(field, 0),
                "heuristic_requested_new_records": requested_records,
                "priority": "high" if total_errors >= 6 else "medium" if total_errors else "none",
                "collection_guidance": FIELD_COLLECTION_GUIDANCE[field],
            }
        )
    field_priorities.sort(
        key=lambda row: (
            -int(row["total_entity_errors"]),
            int(row["current_span_count"]),
            str(row["field"]),
        )
    )
    requested_total = sum(int(row["heuristic_requested_new_records"]) for row in field_priorities)
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "purpose": "Targeted Week 2 human span-data collection plan.",
            "source_paths": source_paths,
            "research_integrity_note": (
                "This plan does not generate command text or gold labels. Any new records must preserve "
                "data_type/source provenance and must not be described as human-written unless a human wrote them."
            ),
        },
        "roadmap_anchor": {
            "week": "Week 2",
            "roadmap_deliverables": [
                "Speech-to-text pipeline",
                "Intent parser",
                "Example command dataset",
            ],
            "roadmap_fields": list(SPAN_FIELDS),
        },
        "literature_anchor": [
            "Build labeled command data with explicit provenance and fixed splits.",
            "Train or fine-tune intent extraction when enough labeled commands exist.",
            "Keep ASR evaluation separate from text intent extraction.",
            "Record model, package versions, parameters, random seed, splits, and raw outputs.",
        ],
        "current_status": {
            "span_dataset": span_summary,
            "reviewed_transformer_test_summary": evaluation_summary,
        },
        "split_policy": {
            "targeted_followup_records": "train_or_validation_only",
            "reason": (
                "This plan is derived from held-out test errors. Do not add targeted follow-up records to the "
                "existing test split and then use them as an unbiased test result."
            ),
            "fresh_test_set_needed": True,
        },
        "field_priorities": field_priorities,
        "recommended_next_batch": {
            "minimum_human_written_span_records": requested_total,
            "record_text_policy": "human_written_or_label_as_synthetic",
            "label_policy": "human_verified_exact_character_spans",
            "completion_criteria": [
                "New records validate with scripts/validate_span_dataset.py.",
                "No normalized command text is duplicated across train, validation, and test splits.",
                "Hugging Face export is regenerated from the updated span dataset.",
                "Transformer retrain is run in Google Colab with a T4 runtime.",
                "Raw metrics, predictions, and error analysis are copied back before interpreting results.",
            ],
        },
    }


def render_week2_collection_plan_markdown(plan: dict[str, Any]) -> str:
    """Render a concise Markdown report for human data collection."""

    lines = [
        "# Week 2 Targeted Span Collection Plan",
        "",
        "This report is derived from the reviewed Colab/T4 transformer error analysis. It does not contain generated command text or new gold labels.",
        "",
        "## Roadmap Anchor",
        "",
        f"- Week: {plan['roadmap_anchor']['week']}",
        "- Deliverables: speech-to-text pipeline, intent parser, example command dataset.",
        f"- Fields: {', '.join(plan['roadmap_anchor']['roadmap_fields'])}",
        "",
        "## Current Reviewed Transformer Result",
        "",
    ]
    summary = plan["current_status"]["reviewed_transformer_test_summary"]
    lines.extend(
        [
            f"- Records: {summary.get('records', 'not stated')}",
            f"- Entity F1: {_format_float(summary.get('entity_f1'))}",
            f"- Entity precision: {_format_float(summary.get('entity_precision'))}",
            f"- Entity recall: {_format_float(summary.get('entity_recall'))}",
            f"- Token accuracy: {_format_float(summary.get('token_accuracy'))}",
            "",
            "## Split Policy",
            "",
            "- Put targeted follow-up records in train or validation only.",
            "- Do not use targeted records derived from held-out test errors as an unbiased test result.",
            "- Create a fresh test set later if these targeted categories become part of model selection.",
            "",
            "## Field Priorities",
            "",
        ]
    )
    for row in plan["field_priorities"]:
        if int(row["total_entity_errors"]) == 0:
            continue
        lines.extend(
            [
                f"### {row['field']}",
                "",
                f"- Priority: {row['priority']}",
                f"- False negatives: {row['false_negative_entities']}",
                f"- False positives: {row['false_positive_entities']}",
                f"- Current span count: {row['current_span_count']}",
                f"- Heuristic requested new records: {row['heuristic_requested_new_records']}",
                "- Collection guidance:",
            ]
        )
        lines.extend(f"  - {item}" for item in row["collection_guidance"])
        lines.append("")
    next_batch = plan["recommended_next_batch"]
    lines.extend(
        [
            "## Next Batch",
            "",
            f"- Minimum human-written span records: {next_batch['minimum_human_written_span_records']}",
            f"- Record text policy: {next_batch['record_text_policy']}",
            f"- Label policy: {next_batch['label_policy']}",
            "",
            "## Completion Criteria",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in next_batch["completion_criteria"])
    lines.append("")
    return "\n".join(lines)


def build_week2_collection_packet(
    plan: dict[str, Any],
    *,
    record_prefix: str = "human_cmd_followup",
    source: str = "manual_week2_span_annotation_v2",
) -> list[dict[str, Any]]:
    """Create blank human collection slots from a targeted collection plan.

    The returned rows are not dataset records. They are a collection worksheet:
    text and spans are intentionally blank until a human writes a command and
    verifies exact span labels.
    """

    packet: list[dict[str, Any]] = []
    sequence = 1
    for priority in plan.get("field_priorities", []):
        requested_records = int(priority.get("heuristic_requested_new_records", 0))
        if requested_records <= 0:
            continue
        field = str(priority["field"])
        for field_index in range(1, requested_records + 1):
            packet.append(
                {
                    "slot_id": f"{record_prefix}_{sequence:03d}",
                    "status": "needs_human_command_and_span_labels",
                    "record_id_suggestion": f"{record_prefix}_{sequence:03d}",
                    "priority_field": field,
                    "priority_field_slot": field_index,
                    "recommended_split": _recommended_followup_split(sequence),
                    "source": source,
                    "data_type": "human_verified_span_command",
                    "text": "",
                    "spans": [],
                    "collection_guidance": list(priority.get("collection_guidance", [])),
                    "research_integrity_note": (
                        "This is a blank collection slot, not a dataset record. Do not train on it until "
                        "a human writes the command text and verifies exact character spans."
                    ),
                    "do_not_use_as_unbiased_test": True,
                }
            )
            sequence += 1
    return packet


def render_week2_collection_packet_markdown(packet: list[dict[str, Any]]) -> str:
    """Render a blank collection worksheet for human command entry."""

    train_count = sum(1 for row in packet if row.get("recommended_split") == "train")
    validation_count = sum(1 for row in packet if row.get("recommended_split") == "validation")
    lines = [
        "# Week 2 Targeted Span Collection Packet",
        "",
        "This is a blank worksheet for real human-written commands and human-verified exact span labels.",
        "",
        "Do not treat any row as collected data until the `text` and `spans` fields are filled and validated.",
        "",
        "## Summary",
        "",
        f"- Total blank slots: {len(packet)}",
        f"- Recommended train slots: {train_count}",
        f"- Recommended validation slots: {validation_count}",
        "- Recommended test slots: 0",
        "",
        "## How To Use",
        "",
        "1. Write one original command for each slot.",
        "2. Label exact spans with `scripts/create_span_record.py` or `scripts/create_span_record_from_command.py`.",
        "3. Keep targeted follow-up records out of the held-out test split.",
        "4. Validate the updated dataset before training.",
        "",
        "## Blank Slots",
        "",
        "| Slot | Split | Priority Field | What To Collect |",
        "| --- | --- | --- | --- |",
    ]
    for row in packet:
        guidance = " ".join(str(item) for item in row.get("collection_guidance", []))
        lines.append(
            f"| `{row['slot_id']}` | `{row['recommended_split']}` | `{row['priority_field']}` | {guidance} |"
        )
    lines.append("")
    return "\n".join(lines)


def _int_counts(raw: Any) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    return {str(key): int(value) for key, value in raw.items()}


def _requested_record_count(total_errors: int) -> int:
    if total_errors <= 0:
        return 0
    return max(3, min(12, total_errors))


def _format_float(value: Any) -> str:
    if isinstance(value, (float, int)):
        return f"{float(value):.4f}"
    return "not stated"


def _recommended_followup_split(sequence: int) -> str:
    return "validation" if sequence % 4 == 0 else "train"
