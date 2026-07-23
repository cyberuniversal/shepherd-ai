"""Merge independent labels and require third-party adjudication for disagreements."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.human_evidence_benchmark import (  # noqa: E402
    adjudicate_records,
    decision_counts,
    index_contexts,
    read_jsonl,
    sha256_file,
    write_jsonl,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author-dataset", type=Path, required=True)
    parser.add_argument("--review-dataset", type=Path, required=True)
    parser.add_argument("--contexts", type=Path, required=True)
    parser.add_argument("--adjudications", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--disagreements-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args()

    author_rows = read_jsonl(args.author_dataset)
    review_rows = read_jsonl(args.review_dataset)
    contexts = index_contexts(read_jsonl(args.contexts))
    adjudication_rows = read_jsonl(args.adjudications) if args.adjudications else []
    final_rows, disagreements = adjudicate_records(
        author_rows, review_rows, contexts, adjudication_rows
    )
    write_jsonl(final_rows, args.output)
    write_jsonl(disagreements, args.disagreements_output)
    unresolved = [
        row for row in disagreements
        if row.get("status") == "requires_third_party_adjudication"
    ]
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "builder": "human_evidence_adjudicator_v1",
        "author_record_count": len(author_rows),
        "final_record_count": len(final_rows),
        "disagreement_count": len(disagreements),
        "unresolved_disagreement_count": len(unresolved),
        "decision_counts": decision_counts(final_rows, "expected_decision"),
        "complete": len(final_rows) == len(author_rows) and not unresolved,
        "inputs": {
            "author_dataset_sha256": sha256_file(args.author_dataset),
            "review_dataset_sha256": sha256_file(args.review_dataset),
            "contexts_sha256": sha256_file(args.contexts),
            "adjudications_sha256": (
                sha256_file(args.adjudications) if args.adjudications else None
            ),
        },
        "outputs": {
            "benchmark": str(args.output),
            "benchmark_sha256": sha256_file(args.output),
            "disagreements": str(args.disagreements_output),
            "disagreements_sha256": sha256_file(args.disagreements_output),
        },
        "claim_status": (
            "labels_adjudicated_not_evaluated"
            if len(final_rows) == len(author_rows) and not unresolved
            else "incomplete_not_usable"
        ),
    }
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
