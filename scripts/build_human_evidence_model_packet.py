"""Build label-separated monolithic-model inputs from an adjudicated benchmark."""

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
    build_model_packet,
    decision_counts,
    index_contexts,
    read_jsonl,
    sha256_file,
    write_jsonl,
)
from shepherd_ai.monolithic_decision import PROMPT_VERSION  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--contexts", type=Path, required=True)
    parser.add_argument("--inputs-output", type=Path, required=True)
    parser.add_argument("--gold-output", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path, required=True)
    args = parser.parse_args()

    benchmark_rows = read_jsonl(args.benchmark)
    contexts = index_contexts(read_jsonl(args.contexts))
    inputs, gold = build_model_packet(benchmark_rows, contexts)
    write_jsonl(inputs, args.inputs_output)
    write_jsonl(gold, args.gold_output)
    manifest = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "builder": "human_evidence_model_packet_builder_v1",
            "python_version": platform.python_version(),
            "prompt_version": PROMPT_VERSION,
            "research_role": "fresh_human_heldout_candidate_not_yet_evaluated",
        },
        "case_count": len(inputs),
        "gold_decision_counts": decision_counts(gold, "expected_decision"),
        "inputs": {
            "path": str(args.inputs_output),
            "sha256": sha256_file(args.inputs_output),
            "contains_gold_labels": False,
        },
        "gold": {
            "path": str(args.gold_output),
            "sha256": sha256_file(args.gold_output),
            "loaded_by_model_runner": False,
        },
        "sources": {
            "benchmark": {
                "path": str(args.benchmark),
                "sha256": sha256_file(args.benchmark),
            },
            "contexts": {
                "path": str(args.contexts),
                "sha256": sha256_file(args.contexts),
            },
        },
        "leakage_controls": [
            "Model inputs contain no expected decision or annotation rationale.",
            "Gold labels are stored in a separate JSONL.",
            "Every context and exact prompt is SHA-256 hashed before inference.",
        ],
    }
    args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
