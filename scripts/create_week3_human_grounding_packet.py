"""Create a blank Week 3 human grounding benchmark collection packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations  # noqa: E402
from shepherd_ai.week3_human_benchmark import (  # noqa: E402
    build_human_grounding_packet,
    render_human_grounding_packet_markdown,
)


DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_JSONL = ROOT / "reports" / "week3_human_grounding_packet.jsonl"
DEFAULT_MARKDOWN = ROOT / "reports" / "week3_human_grounding_packet.md"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--jsonl-output", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--record-prefix", default="human_ground")
    parser.add_argument("--source", default="manual_week3_grounding_benchmark_v1")
    parser.add_argument("--split", default="human_holdout_candidate")
    args = parser.parse_args()

    locations = load_map_locations(args.map)
    packet = build_human_grounding_packet(
        locations,
        record_prefix=args.record_prefix,
        source=args.source,
        split=args.split,
    )

    args.jsonl_output.parent.mkdir(parents=True, exist_ok=True)
    args.jsonl_output.write_text(
        "".join(json.dumps(slot.to_dict(), sort_keys=True) + "\n" for slot in packet),
        encoding="utf-8",
    )

    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(render_human_grounding_packet_markdown(packet), encoding="utf-8")

    print(
        json.dumps(
            {
                "slots": len(packet),
                "jsonl_output": str(args.jsonl_output),
                "markdown_output": str(args.markdown_output),
                "note": "Blank slots are not benchmark data until human-filled and validated.",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
