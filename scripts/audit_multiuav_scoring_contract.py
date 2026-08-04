"""Audit frozen MultiUAV scoring without reading model study outputs."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_scoring import (  # noqa: E402
    SCORING_CONTRACT_VERSION,
    load_official_command_labels,
    scoring_contract,
)
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        type=Path,
        default=ROOT / "external" / "MultiUAV-Plat" / "benchmark" / "benchmark.zip",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT
        / "datasets"
        / "multiuav_plat"
        / "accuracy_case_manifest_v1.json",
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT
        / "datasets"
        / "multiuav_plat"
        / "accuracy_protocol_freeze_v1.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = _read_object(args.manifest)
    protocol = _read_object(args.protocol)
    contract = scoring_contract()
    if protocol.get("scoring_contract_version") != SCORING_CONTRACT_VERSION:
        raise ValueError("protocol does not bind the frozen scoring version")
    if protocol.get("scoring_contract") != contract:
        raise ValueError("protocol scoring contract differs from source code")
    if [
        metric.get("metric_id") for metric in protocol.get("primary_outcomes", [])
    ] != ["unsafe_proceed_rate_nonexecute", "end_to_end_case_success_rate"]:
        raise ValueError("protocol primary outcomes differ from scoring contract")

    labels = load_official_command_labels(args.archive, manifest)
    manifest_rows = manifest.get("cases", [])
    case_counts = Counter(str(row["source_task_id"]) for row in manifest_rows)
    if len(labels) != 284 or set(case_counts.values()) != {5}:
        raise ValueError("official labels do not cover 284 complete test clusters")
    command_counts = Counter(
        command for commands in labels.values() for command in commands
    )
    output = {
        "schema_version": 1,
        "valid": True,
        "scoring_contract": contract,
        "artifact_bindings": {
            "source_archive_sha256": sha256_file(args.archive),
            "accuracy_manifest_sha256": sha256_file(args.manifest),
            "accuracy_protocol_sha256": sha256_file(args.protocol),
        },
        "official_label_audit": {
            "source_clusters": len(labels),
            "manifest_cases": len(manifest_rows),
            "cases_per_source_cluster": 5,
            "command_vocabulary": sorted(command_counts),
            "official_command_occurrences": dict(sorted(command_counts.items())),
            "model_prompt_access": False,
        },
        "study_results": {
            "checkpoint_rows_read": 0,
            "scores_inspected": False,
            "model_invoked": False,
        },
        "source_code_sha256": {
            "multiuav_scoring.py": sha256_file(
                ROOT / "src" / "shepherd_ai" / "multiuav_scoring.py"
            ),
            "audit_multiuav_scoring_contract.py": sha256_file(Path(__file__)),
        },
        "claim_status": "score_blind_scoring_contract_frozen_no_study_results",
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
