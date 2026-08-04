"""Convert reviewer-authored Accept notes into a validated review packet."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_interventions import (  # noqa: E402
    normalize_accepted_review_rows,
    validate_completed_pilot_review,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "datasets" / "multiuav_plat" / "intervention_pilot_v2.json",
    )
    parser.add_argument("--reviewer-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.input.resolve() == args.output.resolve():
        raise ValueError("normalized output must not overwrite the source response")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {args.output}")

    with args.input.open(encoding="utf-8-sig", newline="") as stream:
        source_rows = list(csv.DictReader(stream))
    normalized = normalize_accepted_review_rows(source_rows, args.reviewer_id)
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    summary = validate_completed_pilot_review(dataset, normalized)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(normalized[0]))
        writer.writeheader()
        writer.writerows(normalized)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
