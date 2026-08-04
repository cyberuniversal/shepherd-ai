"""Build the provisional resource source-task subset and condition order."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_interventions import (  # noqa: E402
    classify_intervention_fact_kind,
)
from shepherd_ai.multiuav_methods import METHOD_SPECS  # noqa: E402
from shepherd_ai.multiuav_model_revisions import (  # noqa: E402
    REGISTERED_MODEL_REVISIONS,
)
from shepherd_ai.multiuav_resource_schedule import (  # noqa: E402
    RESOURCE_ORDER_SEED,
    RESOURCE_SELECTION_SEED,
    build_condition_schedule,
    select_resource_source_tasks,
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
        "--output",
        type=Path,
        default=ROOT
        / "datasets"
        / "multiuav_plat"
        / "resource_schedule_candidate_v1.json",
    )
    args = parser.parse_args()

    archive_hash = sha256_file(args.archive)
    if archive_hash != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("benchmark archive does not match the pinned SHA-256")
    eligibility = json.loads(args.eligibility.read_text(encoding="utf-8"))
    if eligibility.get("source_archive_sha256") != archive_hash:
        raise ValueError("eligibility manifest is not bound to the source archive")

    test_ids = {
        str(row["task_id"])
        for row in eligibility["records"]
        if row.get("eligible") and row.get("split") == "test"
    }
    source_texts = _load_source_texts(args.archive, test_ids)
    if set(source_texts) != test_ids:
        raise ValueError("source archive did not contain every eligible test task")
    fact_kinds = {
        task_id: classify_intervention_fact_kind(text)
        for task_id, text in source_texts.items()
    }
    selected = select_resource_source_tasks(
        eligibility["records"],
        supported_task_ids=set(fact_kinds),
    )
    for row in selected:
        row["supported_intervention_fact_kind"] = fact_kinds[row["task_id"]]

    schedule = build_condition_schedule(
        model_ids=tuple(item.model_id for item in REGISTERED_MODEL_REVISIONS),
        method_ids=tuple(item.method_id for item in METHOD_SPECS),
    )
    stratum_counts = Counter(
        f"{row['scenario']}|{row['difficulty']}" for row in selected
    )
    fact_kind_counts = Counter(
        str(row["supported_intervention_fact_kind"]) for row in selected
    )
    planned_cases = len(selected) * 5
    artifact = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_archive_sha256": archive_hash,
        "eligibility_sha256": sha256_file(args.eligibility),
        "source_code_sha256": {
            "multiuav_resource_schedule.py": sha256_file(
                ROOT / "src" / "shepherd_ai" / "multiuav_resource_schedule.py"
            ),
            "build_multiuav_resource_schedule.py": sha256_file(Path(__file__)),
        },
        "selection": {
            "seed": RESOURCE_SELECTION_SEED,
            "split": "test",
            "strategy": "lowest_sha256_rank_two_per_scenario_difficulty_stratum",
            "source_tasks": selected,
            "stratum_counts": dict(sorted(stratum_counts.items())),
            "supported_intervention_fact_kind_counts": dict(
                sorted(fact_kind_counts.items())
            ),
        },
        "condition_schedule": {
            "seed": RESOURCE_ORDER_SEED,
            "strategy": "sha256_rank_per_repetition",
            "rows": schedule,
        },
        "summary": {
            "source_tasks": len(selected),
            "strata": len(stratum_counts),
            "planned_cases": planned_cases,
            "models": len(REGISTERED_MODEL_REVISIONS),
            "methods": len(METHOD_SPECS),
            "repetitions": 3,
            "conditions": len(schedule),
            "planned_method_case_rows": planned_cases * len(schedule),
        },
        "model_invocation": {
            "performed": False,
            "study_cases_used": False,
        },
        "claim_status": "candidate_source_subset_and_condition_order_only",
        "limitations": [
            "The selected source tasks do not yet have approved five-case clusters.",
            "This artifact is not an evaluation dataset, run config, or result.",
            "Selection must be revalidated against the complete approved test dataset.",
            "Warm-up, thermal-start, and background-workload controls remain unresolved.",
            "No model was loaded or invoked.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifact["summary"], indent=2, sort_keys=True))


def _load_source_texts(archive: Path, selected_ids: set[str]) -> dict[str, str]:
    records: dict[str, str] = {}
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
                records[task_id] = str(task["content"])
    return records


if __name__ == "__main__":
    main()
