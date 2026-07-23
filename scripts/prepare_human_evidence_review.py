"""Create a label-blinded review packet from human-authored benchmark records."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.human_evidence_benchmark import (  # noqa: E402
    index_contexts,
    prepare_blinded_review,
    read_jsonl,
    sha256_file,
    write_jsonl,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author-dataset", type=Path, required=True)
    parser.add_argument("--contexts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path, required=True)
    args = parser.parse_args()

    contexts = index_contexts(read_jsonl(args.contexts))
    packet = prepare_blinded_review(read_jsonl(args.author_dataset), contexts)
    write_jsonl(packet, args.output)
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "builder": "human_evidence_blinded_review_builder_v1",
        "python_version": platform.python_version(),
        "record_count": len(packet),
        "author_dataset": {
            "path": str(args.author_dataset),
            "sha256": sha256_file(args.author_dataset),
        },
        "contexts": {"path": str(args.contexts), "sha256": sha256_file(args.contexts)},
        "review_packet": {
            "path": str(args.output),
            "sha256": sha256_file(args.output),
            "contains_author_labels": False,
            "contains_author_identity": False,
        },
    }
    args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
