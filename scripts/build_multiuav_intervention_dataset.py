"""Build the complete eligible five-way intervention dataset and review packet."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_interventions import (  # noqa: E402
    VARIANTS,
    build_draft_cluster,
    compact_review_rows,
)
from shepherd_ai.multiuav_source import (  # noqa: E402
    EXPECTED_ARCHIVE_SHA256,
    EXPECTED_TASK_COUNT,
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
    parser.add_argument("--dataset-output", type=Path, required=True)
    parser.add_argument("--review-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args()

    archive_hash = sha256_file(args.archive)
    if archive_hash != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("benchmark archive does not match the pinned SHA-256")
    eligibility = json.loads(args.eligibility.read_text(encoding="utf-8"))
    if eligibility.get("source_archive_sha256") != archive_hash:
        raise ValueError("eligibility manifest is not bound to the source archive")
    records = eligibility.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_TASK_COUNT:
        raise ValueError("eligibility manifest must contain all 1,500 source tasks")
    eligible_by_id = {
        str(row["task_id"]): row for row in records if row.get("eligible")
    }
    source_by_id = _load_selected_source(args.archive, set(eligible_by_id))
    if set(source_by_id) != set(eligible_by_id):
        raise ValueError("source archive did not contain every eligible task")

    clusters = [
        build_draft_cluster(
            source_by_id[task_id]["session"],
            source_by_id[task_id]["task"],
            eligible_by_id[task_id],
        )
        for task_id in sorted(eligible_by_id)
    ]
    generated_at = datetime.now(timezone.utc).isoformat()
    dataset = {
        "schema_version": 1,
        "metadata": {
            "generated_at_utc": generated_at,
            "source_archive_sha256": archive_hash,
            "eligibility_sha256": sha256_file(args.eligibility),
            "selection_strategy": "all_eligible_source_tasks",
            "data_status": "template_generated_unreviewed_dataset",
            "claim_status": "draft_construction_not_evaluation_data",
        },
        "clusters": clusters,
    }
    args.dataset_output.parent.mkdir(parents=True, exist_ok=True)
    args.dataset_output.write_text(
        json.dumps(dataset, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    review_rows = [
        row for cluster in clusters for row in compact_review_rows(cluster)
    ]
    args.review_output.parent.mkdir(parents=True, exist_ok=True)
    with args.review_output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(review_rows[0]))
        writer.writeheader()
        writer.writerows(review_rows)

    split_clusters = Counter(cluster["split"] for cluster in clusters)
    fact_kinds = Counter(
        cluster["intervention"]["missing_fact_kind"] for cluster in clusters
    )
    exclusion_reasons = Counter(
        str(row.get("exclusion_reason") or "not_stated")
        for row in records
        if not row.get("eligible")
    )
    summary = {
        "schema_version": 1,
        "generated_at_utc": generated_at,
        "source_archive_sha256": archive_hash,
        "eligibility_sha256": sha256_file(args.eligibility),
        "dataset_sha256": sha256_file(args.dataset_output),
        "review_packet_sha256": sha256_file(args.review_output),
        "summary": {
            "source_tasks": len(records),
            "eligible_clusters": len(clusters),
            "excluded_source_tasks": len(records) - len(clusters),
            "planned_pre_exclusion_cases": len(records) * len(VARIANTS),
            "generated_post_eligibility_cases": len(review_rows),
            "review_rows": len(review_rows),
            "cases_per_cluster": len(VARIANTS),
            "split_cluster_counts": dict(sorted(split_clusters.items())),
            "split_case_counts": {
                split: count * len(VARIANTS)
                for split, count in sorted(split_clusters.items())
            },
            "missing_fact_kind_counts": dict(sorted(fact_kinds.items())),
            "exclusion_reason_counts": dict(sorted(exclusion_reasons.items())),
            "pending_human_review_clusters": len(clusters),
            "approved_clusters": 0,
        },
        "claim_status": "full_draft_generated_human_review_not_started",
        "limitations": [
            "All generated decisions and text transformations remain unreviewed.",
            "The 27 ineligible source tasks remain excluded with recorded reasons.",
            "No generated case may enter model inference or publication summaries.",
        ],
    }
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary["summary"], indent=2, sort_keys=True))


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
