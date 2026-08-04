"""Record the completed pilot review as stratified expert construction QC."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_protocol import build_expert_qc_audit  # noqa: E402
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pilot-dataset",
        type=Path,
        default=ROOT / "datasets" / "multiuav_plat" / "intervention_pilot_v2.json",
    )
    parser.add_argument(
        "--full-dataset",
        type=Path,
        default=ROOT / "datasets" / "multiuav_plat" / "intervention_dataset_v1.json",
    )
    parser.add_argument(
        "--review-validation",
        type=Path,
        default=ROOT
        / "datasets"
        / "multiuav_plat"
        / "intervention_pilot_review_validation_v2.json",
    )
    parser.add_argument("--reviewer-id", required=True)
    parser.add_argument("--reviewer-role", required=True)
    parser.add_argument("--reviewer-qualification", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    pilot = _read_object(args.pilot_dataset)
    full = _read_object(args.full_dataset)
    review = _read_object(args.review_validation)
    audit = build_expert_qc_audit(
        pilot,
        full,
        review,
        reviewer_id=args.reviewer_id,
        reviewer_role=args.reviewer_role,
        reviewer_qualification=args.reviewer_qualification,
    )
    output = {
        "schema_version": 1,
        **audit,
        "artifact_bindings": {
            "pilot_dataset_sha256": sha256_file(args.pilot_dataset),
            "full_dataset_sha256": sha256_file(args.full_dataset),
            "review_validation_sha256": sha256_file(args.review_validation),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, sort_keys=True))


def _read_object(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


if __name__ == "__main__":
    main()
