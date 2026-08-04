"""Validate the stored MultiUAV intervention pilot and review packet."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_interventions import (  # noqa: E402
    validate_unreviewed_pilot_dataset,
)
from shepherd_ai.multiuav_source import (  # noqa: E402
    EXPECTED_ARCHIVE_SHA256,
    sha256_file,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        type=Path,
        default=ROOT / "external" / "MultiUAV-Plat" / "benchmark" / "benchmark.zip",
    )
    parser.add_argument(
        "--eligibility",
        type=Path,
        default=ROOT / "datasets" / "multiuav_plat" / "task_eligibility_v1.json",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "datasets" / "multiuav_plat" / "intervention_pilot_v2.json",
    )
    parser.add_argument(
        "--review-packet",
        type=Path,
        default=ROOT / "reports" / "multiuav_intervention_pilot_review_v2.csv",
    )
    parser.add_argument(
        "--generation-summary",
        type=Path,
        default=ROOT
        / "datasets"
        / "multiuav_plat"
        / "intervention_pilot_summary_v2.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    archive_hash = sha256_file(args.archive)
    if archive_hash != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("benchmark archive does not match the pinned SHA-256")
    eligibility = _read_object(args.eligibility)
    dataset = _read_object(args.dataset)
    generation_summary = _read_object(args.generation_summary)
    if dataset["metadata"].get("source_archive_sha256") != archive_hash:
        raise ValueError("pilot dataset is not bound to the pinned source")
    eligibility_hash = sha256_file(args.eligibility)
    if dataset["metadata"].get("eligibility_sha256") != eligibility_hash:
        raise ValueError("pilot dataset is not bound to task eligibility")
    if generation_summary.get("dataset_sha256") != sha256_file(args.dataset):
        raise ValueError("generation summary dataset hash does not match")
    if generation_summary.get("review_packet_sha256") != sha256_file(
        args.review_packet
    ):
        raise ValueError("generation summary review-packet hash does not match")

    with args.review_packet.open(encoding="utf-8-sig", newline="") as stream:
        review_rows = list(csv.DictReader(stream))
    eligible_train_ids = {
        str(row["task_id"])
        for row in eligibility["records"]
        if row.get("eligible") and row.get("split") == "train"
    }
    source_by_id = _load_selected_source(args.archive, eligible_train_ids)
    result = validate_unreviewed_pilot_dataset(
        dataset,
        review_rows,
        eligibility["records"],
        source_by_id,
        expected_per_stratum=int(
            dataset["metadata"]["per_scenario_difficulty_stratum"]
        ),
    )
    output = {
        "schema_version": 2,
        "valid": True,
        "source_archive_sha256": archive_hash,
        "eligibility_sha256": eligibility_hash,
        "dataset_sha256": sha256_file(args.dataset),
        "review_packet_sha256": sha256_file(args.review_packet),
        "generation_summary_sha256": sha256_file(args.generation_summary),
        "summary": result,
        "claim_status": "unreviewed_pilot_validated_not_evaluation_data",
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


def _load_selected_source(
    archive: Path,
    selected_ids: set[str],
) -> dict[str, dict]:
    records: dict[str, dict] = {}
    with ZipFile(archive) as bundle:
        for member in sorted(
            name for name in bundle.namelist() if name.lower().endswith(".json")
        ):
            session = json.loads(bundle.read(member))
            for task in session["tasks"]:
                task_id = str(task["id"])
                if task_id not in selected_ids:
                    continue
                if task_id in records:
                    raise ValueError(f"duplicate selected source task: {task_id}")
                records[task_id] = {"session": session, "task": task}
    return records


if __name__ == "__main__":
    main()
