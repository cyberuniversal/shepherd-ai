"""Audit recoverability and resource-conflict rules on eligible source tasks."""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_context import (  # noqa: E402
    project_agent_visible_context,
    validate_agent_visible_context,
)
from shepherd_ai.multiuav_recoverability import (  # noqa: E402
    assess_resource_conflict,
    detect_operator_fact_candidates,
    extract_explicit_drone_references,
    recoverability_policy_manifest,
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    archive_hash = sha256_file(args.archive)
    if archive_hash != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("benchmark archive does not match the pinned SHA-256")
    eligibility = json.loads(args.eligibility.read_text(encoding="utf-8"))
    if eligibility.get("source_archive_sha256") != archive_hash:
        raise ValueError("eligibility manifest is not bound to the source archive")
    eligible_ids = {
        row["task_id"] for row in eligibility["records"] if row["eligible"]
    }

    fact_counts: Counter[str] = Counter()
    resource_basis_counts: Counter[str] = Counter()
    audited_ids: set[str] = set()
    missing_candidate_ids: list[str] = []
    failed_conflict_ids: list[str] = []
    with ZipFile(args.archive) as bundle:
        for member in sorted(
            name for name in bundle.namelist() if name.lower().endswith(".json")
        ):
            session = json.loads(bundle.read(member))
            for task in session["tasks"]:
                task_id = task["id"]
                if task_id not in eligible_ids:
                    continue
                audited_ids.add(task_id)
                instruction = task["content"]
                candidates = detect_operator_fact_candidates(instruction)
                if not candidates:
                    missing_candidate_ids.append(task_id)
                fact_counts.update(candidates)

                context = project_agent_visible_context(
                    session,
                    task_id=task_id,
                    instruction=instruction,
                )
                references = extract_explicit_drone_references(instruction)
                conflict_context = deepcopy(context)
                if references:
                    required = set(references)
                    conflict_context["drones"] = [
                        drone
                        for drone in context["drones"]
                        if _normalize(str(drone.get("name", ""))) not in required
                    ]
                    assessment = assess_resource_conflict(
                        conflict_context,
                        required_drone_references=references,
                    )
                    resource_basis_counts["explicit_required_uav_absence"] += 1
                else:
                    conflict_context["drones"] = []
                    assessment = assess_resource_conflict(
                        conflict_context,
                        required_count=1,
                    )
                    resource_basis_counts["zero_fleet_for_generic_uav_task"] += 1
                validate_agent_visible_context(conflict_context)
                if not assessment.block_allowed:
                    failed_conflict_ids.append(task_id)

    if audited_ids != eligible_ids:
        raise ValueError("recoverability audit did not cover exactly eligible tasks")
    if missing_candidate_ids:
        raise ValueError(
            f"eligible tasks without operator-fact candidates: {missing_candidate_ids}"
        )
    if failed_conflict_ids:
        raise ValueError(
            f"counterfactual fleet conflicts did not justify BLOCK: {failed_conflict_ids}"
        )

    policy = recoverability_policy_manifest()
    result = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_archive_sha256": archive_hash,
        "eligibility_sha256": sha256_file(args.eligibility),
        "policy": policy,
        "policy_sha256": _sha256_json(policy),
        "summary": {
            "eligible_tasks_audited": len(audited_ids),
            "tasks_with_operator_fact_candidates": (
                len(audited_ids) - len(missing_candidate_ids)
            ),
            "candidate_fact_counts": dict(sorted(fact_counts.items())),
            "resource_conflict_basis_counts": dict(
                sorted(resource_basis_counts.items())
            ),
            "resource_conflict_block_justifications": (
                len(audited_ids) - len(failed_conflict_ids)
            ),
        },
        "claim_status": "recoverability_policy_and_candidate_coverage_audited_only",
        "limitations": [
            "Candidate detection inventories source wording but does not remove text or assign final labels.",
            "Counterfactual fleet contexts prove policy behavior, not semantic quality of generated cases.",
            "No missing-information, restored-information, or resource-conflict case was generated.",
            "Every generated derivative still requires validation and registered human review.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())


def _sha256_json(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


if __name__ == "__main__":
    main()
