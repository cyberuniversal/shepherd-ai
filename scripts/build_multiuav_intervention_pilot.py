"""Build a training-only five-way intervention pilot and compact review packet."""

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
    PILOT_SEED,
    VARIANTS,
    build_draft_cluster,
    classify_intervention_fact_kind,
    compact_review_rows,
    select_stratified_training_pilot,
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
        default=ROOT
        / "datasets"
        / "multiuav_plat"
        / "task_eligibility_v1.json",
    )
    parser.add_argument("--dataset-output", type=Path, required=True)
    parser.add_argument("--review-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--per-stratum", type=int, default=2)
    parser.add_argument("--seed", default=PILOT_SEED)
    args = parser.parse_args()

    archive_hash = sha256_file(args.archive)
    if archive_hash != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("benchmark archive does not match the pinned SHA-256")
    eligibility = json.loads(args.eligibility.read_text(encoding="utf-8"))
    if eligibility.get("source_archive_sha256") != archive_hash:
        raise ValueError("eligibility manifest is not bound to the source archive")
    eligible_train_ids = {
        str(row["task_id"])
        for row in eligibility["records"]
        if row.get("eligible") and row.get("split") == "train"
    }
    source_by_id = _load_selected_source(args.archive, eligible_train_ids)
    fact_kind_by_task_id = {
        task_id: classify_intervention_fact_kind(str(source["task"]["content"]))
        for task_id, source in source_by_id.items()
    }
    selected = select_stratified_training_pilot(
        eligibility["records"],
        per_stratum=args.per_stratum,
        seed=args.seed,
        fact_kind_by_task_id=fact_kind_by_task_id,
    )
    selected_by_id = {row["task_id"]: row for row in selected}
    if not set(selected_by_id).issubset(source_by_id):
        raise ValueError("source archive did not contain every selected pilot task")

    clusters = [
        build_draft_cluster(
            source_by_id[task_id]["session"],
            source_by_id[task_id]["task"],
            selected_by_id[task_id],
        )
        for task_id in sorted(selected_by_id)
    ]
    expected_cluster_count = args.per_stratum * 15
    if len(clusters) != expected_cluster_count:
        raise ValueError(
            f"pilot has {len(clusters)} clusters; expected {expected_cluster_count}"
        )
    dataset = {
        "schema_version": 2,
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_archive_sha256": archive_hash,
            "eligibility_sha256": sha256_file(args.eligibility),
            "selection_seed": args.seed,
            "selection_strategy": "balanced_fact_kind_per_stratum",
            "per_scenario_difficulty_stratum": args.per_stratum,
            "split": "train",
            "data_status": "template_generated_unreviewed_pilot",
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

    strata = Counter(
        f"{cluster['scenario']}|{cluster['difficulty']}" for cluster in clusters
    )
    fact_kinds = Counter(
        cluster["intervention"]["missing_fact_kind"] for cluster in clusters
    )
    summary = {
        "schema_version": 2,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_archive_sha256": archive_hash,
        "eligibility_sha256": sha256_file(args.eligibility),
        "dataset_sha256": sha256_file(args.dataset_output),
        "review_packet_sha256": sha256_file(args.review_output),
        "summary": {
            "clusters": len(clusters),
            "cases": sum(len(cluster["cases"]) for cluster in clusters),
            "review_rows": len(review_rows),
            "cases_per_cluster": len(VARIANTS),
            "split_counts": {"train": len(clusters)},
            "stratum_counts": dict(sorted(strata.items())),
            "missing_fact_kind_counts": dict(sorted(fact_kinds.items())),
            "pending_human_review_clusters": sum(
                cluster["review_status"] == "pending_human_review"
                for cluster in clusters
            ),
            "approved_clusters": 0,
        },
        "claim_status": "pilot_generation_completed_human_review_not_started",
        "limitations": [
            "This pilot uses training clusters only.",
            "All proposed decisions and template rewrites remain unreviewed.",
            (
                "No pilot case may enter calibration, test, model inference, "
                "or publication summaries."
            ),
            (
                "The compact per-case CSV contains one exact instruction and "
                "short entity, UAV-status, and intervention summaries per row."
            ),
            (
                "Reviewer fields are intentionally blank; no reviewer identity "
                "or judgment was fabricated."
            ),
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
                if task["id"] not in selected_ids:
                    continue
                if task["id"] in records:
                    raise ValueError(f"duplicate selected source task: {task['id']}")
                records[task["id"]] = {"session": session, "task": task}
    return records


if __name__ == "__main__":
    main()
