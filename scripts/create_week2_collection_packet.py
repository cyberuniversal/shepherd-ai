"""Create a blank Week 2 human span-collection packet from a collection plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week2_collection_planning import (  # noqa: E402
    build_week2_collection_packet,
    render_week2_collection_packet_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, help="Targeted collection plan JSON.")
    parser.add_argument("--jsonl-output", required=True, help="Blank collection packet JSONL output.")
    parser.add_argument("--markdown-output", required=True, help="Blank collection packet Markdown output.")
    parser.add_argument("--record-prefix", default="human_cmd_followup", help="Prefix for suggested record IDs.")
    parser.add_argument(
        "--source",
        default="manual_week2_span_annotation_v2",
        help="Source value to use when the blank slots become verified records.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan_path = Path(args.plan)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    packet = build_week2_collection_packet(
        plan,
        record_prefix=args.record_prefix,
        source=args.source,
    )

    jsonl_output_path = Path(args.jsonl_output)
    jsonl_output_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_output_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in packet),
        encoding="utf-8",
    )

    markdown_output_path = Path(args.markdown_output)
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.write_text(render_week2_collection_packet_markdown(packet), encoding="utf-8")

    print(
        json.dumps(
            {
                "slots": len(packet),
                "jsonl_output": str(jsonl_output_path),
                "markdown_output": str(markdown_output_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
