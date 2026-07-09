"""Create a human span-labeling packet from transcript-intent failures."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", required=True, help="Transcript intent evaluation JSON.")
    parser.add_argument("--gold-commands", required=True, help="Human-reviewed audio intent JSONL.")
    parser.add_argument("--system", default="hybrid_span_parser", help="System whose failures should seed the packet.")
    parser.add_argument("--jsonl-output", required=True, help="Packet JSONL output.")
    parser.add_argument("--markdown-output", required=True, help="Packet Markdown output.")
    parser.add_argument("--source", default="manual_week2_audio_span_remediation_v1")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    packet = build_packet(
        evaluation=_load_json(args.evaluation),
        gold_records=_load_jsonl(args.gold_commands),
        system=args.system,
        source=args.source,
        metadata={
            "evaluation": args.evaluation,
            "gold_commands": args.gold_commands,
        },
    )
    jsonl_output = Path(args.jsonl_output)
    jsonl_output.parent.mkdir(parents=True, exist_ok=True)
    jsonl_output.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in packet["records"]),
        encoding="utf-8",
    )

    markdown_output = Path(args.markdown_output)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(render_markdown(packet), encoding="utf-8")
    print(json.dumps(packet["summary"], indent=2, sort_keys=True))


def build_packet(
    *,
    evaluation: dict[str, Any],
    gold_records: list[dict[str, Any]],
    system: str,
    source: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    gold_by_audio_id = {str(record["audio_id"]): record for record in gold_records}
    packet_records: list[dict[str, Any]] = []
    skipped_no_gold: list[str] = []
    for row in evaluation.get("records", []):
        if row.get("system") != system or row.get("all_fields_match"):
            continue
        audio_id = str(row.get("id"))
        gold = gold_by_audio_id.get(audio_id)
        if gold is None:
            skipped_no_gold.append(audio_id)
            continue
        failed_fields = [
            field for field, matched in dict(row.get("field_matches") or {}).items() if not matched
        ]
        packet_records.append(
            {
                "id": f"{audio_id}_span_remediation",
                "audio_id": audio_id,
                "base_intent_record_id": str(gold.get("id")),
                "audio_path": gold.get("audio_path"),
                "text": gold.get("text"),
                "split": gold.get("split", row.get("split", "not stated")),
                "source": source,
                "data_type": "human_verified_audio_span_command_candidate",
                "label_status": "needs_human_span_review",
                "expected_intent": gold.get("expected_intent"),
                "failed_intent_fields": failed_fields,
                "model_actual_intent": row.get("actual_intent"),
                "model_system": system,
                "review_instruction": (
                    "Add exact character spans for action/count/location/target/constraint fields that are "
                    "present in the transcript. Leave absent fields unlabeled. Do not copy model spans as gold "
                    "without human review."
                ),
                "spans": [],
            }
        )

    failed_field_counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    for record in packet_records:
        failed_field_counts.update(record["failed_intent_fields"])
        split_counts[str(record["split"])] += 1

    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "note": (
                "Human span-labeling remediation packet. Records are selected from transcript-intent failures. "
                "The packet does not contain gold spans until a human adds and verifies exact offsets."
            ),
            "system": system,
            "source": source,
            "skipped_no_gold_audio_ids": skipped_no_gold,
            **metadata,
        },
        "summary": {
            "records": len(packet_records),
            "split_counts": dict(sorted(split_counts.items())),
            "failed_field_counts": dict(sorted(failed_field_counts.items())),
            "label_status_counts": dict(Counter(record["label_status"] for record in packet_records)),
        },
        "records": packet_records,
    }


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# Week 2 Audio Span Remediation Packet",
        "",
        packet["metadata"]["note"],
        "",
        "## Summary",
        "",
        f"- Records: {packet['summary']['records']}",
        f"- System: `{packet['metadata']['system']}`",
        f"- Split counts: `{json.dumps(packet['summary']['split_counts'], sort_keys=True)}`",
        f"- Failed field counts: `{json.dumps(packet['summary']['failed_field_counts'], sort_keys=True)}`",
        "",
        "## Review Rules",
        "",
        "- Add exact character spans only after human review of the transcript.",
        "- Use allowed fields: `action`, `count`, `location`, `target`, `constraint`.",
        "- Do not label an intent field that is not explicitly present in the transcript.",
        "- Do not use model output as gold labels.",
        "- Keep these records out of clean test claims if they are used to improve the model or assembly layer.",
        "",
        "## Records",
        "",
        "| ID | Split | Failed fields | Transcript | Expected intent | Model intent |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for record in packet["records"]:
        lines.append(
            f"| `{record['id']}` | `{record['split']}` | "
            f"`{', '.join(record['failed_intent_fields'])}` | "
            f"{record['text']} | "
            f"`{json.dumps(record['expected_intent'], sort_keys=True)}` | "
            f"`{json.dumps(record['model_actual_intent'], sort_keys=True)}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


if __name__ == "__main__":
    main()
