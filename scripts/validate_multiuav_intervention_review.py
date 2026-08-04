"""Validate a completed human review of the MultiUAV intervention pilot."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_interventions import (  # noqa: E402
    validate_completed_pilot_review,
)
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "datasets" / "multiuav_plat" / "intervention_pilot_v2.json",
    )
    parser.add_argument("--review-packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    with args.review_packet.open(encoding="utf-8-sig", newline="") as stream:
        review_rows = list(csv.DictReader(stream))
    result = validate_completed_pilot_review(dataset, review_rows)
    output = {
        "schema_version": 2,
        "valid": True,
        "dataset_sha256": sha256_file(args.dataset),
        "review_packet_sha256": sha256_file(args.review_packet),
        "summary": result,
        "claim_status": (
            "review_packet_structurally_valid_"
            "identity_provenance_requires_project_attestation"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
