"""Freeze MultiUAV-Plat task eligibility and official-alias selection."""

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
    build_task_eligibility,
    load_session_records,
    sha256_file,
    summarize_task_eligibility,
)


DEFAULT_SEED = "shepherd-multiuav-eligibility-v1"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        type=Path,
        default=ROOT / "external" / "MultiUAV-Plat" / "benchmark" / "benchmark.zip",
    )
    parser.add_argument(
        "--session-split",
        type=Path,
        default=ROOT / "datasets" / "multiuav_plat" / "session_split_v1.json",
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
    split = json.loads(args.session_split.read_text(encoding="utf-8"))
    if split.get("source_archive_sha256") != archive_sha256:
        raise ValueError("session split is not bound to the supplied source archive")
    assignments = split.get("assignments")
    if not isinstance(assignments, list):
        raise ValueError("session split assignments must be a list")

    records = load_session_records(args.archive)
    eligibility = build_task_eligibility(
        records,
        assignments,
        seed=args.seed,
    )
    summary = summarize_task_eligibility(eligibility)
    result = {
        "schema_version": 1,
        "source_archive_sha256": archive_sha256,
        "session_split_sha256": sha256_file(args.session_split),
        "seed": args.seed,
        "canonical_ownership": (
            "owner split has maximum task support; ties use "
            "sha256(seed + NUL + normalized_canonical + NUL + split)"
        ),
        "alias_ownership": (
            "owner split has maximum retained-task support; ties use "
            "sha256(seed + NUL + alias-owner + NUL + normalized_alias + NUL + split)"
        ),
        "alias_selection": (
            "lowest sha256(seed + NUL + task_id + NUL + "
            "normalized_alias), then source alias index"
        ),
        "summary": summary,
        "records": eligibility,
        "claim_status": "task_eligibility_and_official_alias_selection_frozen",
        "limitations": [
            "Eligibility is a deterministic leakage-control policy, not a quality label.",
            "Excluded source tasks remove their complete proposed five-case cluster.",
            "The selected alias is upstream-authored but has not been semantically adjudicated.",
            "No missing-information or resource-conflict interventions were generated.",
            "No model prompts, executions, or evaluation results were produced.",
        ],
    }
    _validate_expected_result(summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


def _validate_expected_result(summary: dict[str, object]) -> None:
    expected = {
        "source_task_count": 1_500,
        "eligible_task_count": 1_473,
        "excluded_task_count": 27,
        "five_case_variant_count": 7_365,
        "normalized_cross_split_overlap_count": 0,
    }
    mismatches = {
        key: {"expected": value, "actual": summary.get(key)}
        for key, value in expected.items()
        if summary.get(key) != value
    }
    if mismatches:
        raise ValueError(f"task eligibility result mismatch: {mismatches}")
    if Counter(summary["eligible_task_counts_by_split"]) != Counter(
        {"train": 899, "calibration": 290, "test": 284}
    ):
        raise ValueError("eligible task split counts do not match the frozen audit")


if __name__ == "__main__":
    main()
