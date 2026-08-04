"""Create a separate intervention-pilot review copy for a real reviewer."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_interventions import (  # noqa: E402
    prepare_pilot_review_rows,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--template",
        type=Path,
        default=ROOT / "reports" / "multiuav_intervention_pilot_review_v2.csv",
    )
    parser.add_argument("--reviewer-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.template.resolve() == args.output.resolve():
        raise ValueError("review output must not overwrite the frozen template")
    with args.template.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("review template is empty")
    prepared = prepare_pilot_review_rows(rows, args.reviewer_id)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(prepared[0]))
        writer.writeheader()
        writer.writerows(prepared)
    print(f"Created {len(prepared)} review rows at {args.output}")


if __name__ == "__main__":
    main()
