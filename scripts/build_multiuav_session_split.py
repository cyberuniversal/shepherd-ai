"""Build the preregistered MultiUAV-Plat session split and overlap audit."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_source import (  # noqa: E402
    EXPECTED_ARCHIVE_SHA256,
    audit_instruction_overlap,
    build_stratified_session_split,
    load_session_records,
    sha256_file,
)


DEFAULT_SEED = "shepherd-multiuav-split-v1"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        type=Path,
        default=ROOT / "external" / "MultiUAV-Plat" / "benchmark" / "benchmark.zip",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", default=DEFAULT_SEED)
    args = parser.parse_args()

    archive_sha256 = sha256_file(args.archive)
    if archive_sha256 != EXPECTED_ARCHIVE_SHA256:
        raise ValueError(
            "benchmark archive SHA-256 mismatch: "
            f"expected {EXPECTED_ARCHIVE_SHA256}, got {archive_sha256}"
        )
    records = load_session_records(args.archive)
    assignments = build_stratified_session_split(records, seed=args.seed)
    split_counts = Counter(row["split"] for row in assignments)
    stratum_split_counts: dict[str, Counter[str]] = {}
    for row in assignments:
        key = f"{row['scenario']}|{row['difficulty']}"
        stratum_split_counts.setdefault(key, Counter())[row["split"]] += 1

    result = {
        "schema_version": 1,
        "source_archive_sha256": archive_sha256,
        "seed": args.seed,
        "ranking": "sha256(seed + NUL + session_id), ascending",
        "allocation_per_scenario_difficulty_stratum": {
            "train": 3,
            "calibration": 1,
            "test": 1,
        },
        "session_counts": dict(sorted(split_counts.items())),
        "stratum_split_counts": {
            key: dict(sorted(counts.items()))
            for key, counts in sorted(stratum_split_counts.items())
        },
        "instruction_overlap": audit_instruction_overlap(records, assignments),
        "assignments": assignments,
        "claim_status": "session_split_frozen_source_metadata_only",
        "limitations": [
            "The split does not establish task eligibility.",
            "Cross-split canonical duplicates must be excluded before variant generation.",
            "One official alias per retained task must be selected without cross-split leakage.",
            "No intervention variants, labels, model prompts, or results were generated.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
