"""Approve the held-out controlled-derivative cases under the frozen protocol."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_evaluation_data import (  # noqa: E402
    build_accuracy_case_manifest,
    load_accuracy_evaluation_cases,
)
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "datasets" / "multiuav_plat" / "intervention_dataset_v1.json",
    )
    parser.add_argument(
        "--dataset-validation",
        type=Path,
        default=ROOT
        / "datasets"
        / "multiuav_plat"
        / "intervention_dataset_validation_v1.json",
    )
    parser.add_argument(
        "--expert-qc",
        type=Path,
        default=ROOT / "datasets" / "multiuav_plat" / "expert_qc_audit_v1.json",
    )
    parser.add_argument(
        "--protocol-freeze",
        type=Path,
        default=ROOT
        / "datasets"
        / "multiuav_plat"
        / "accuracy_protocol_freeze_v1.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    dataset = _read_object(args.dataset)
    dataset_validation = _read_object(args.dataset_validation)
    expert_qc = _read_object(args.expert_qc)
    protocol = _read_object(args.protocol_freeze)
    if dataset_validation.get("dataset_sha256") != sha256_file(args.dataset):
        raise ValueError("dataset validation is not bound to the full dataset")
    manifest = build_accuracy_case_manifest(
        dataset,
        dataset_validation,
        expert_qc,
        protocol,
    )
    materialized = load_accuracy_evaluation_cases(dataset, manifest)
    if len(materialized) != manifest["case_count"]:
        raise ValueError("approved manifest did not materialize completely")
    output = {
        **manifest,
        "artifact_bindings": {
            "dataset_sha256": sha256_file(args.dataset),
            "dataset_validation_sha256": sha256_file(args.dataset_validation),
            "expert_qc_sha256": sha256_file(args.expert_qc),
            "protocol_freeze_sha256": sha256_file(args.protocol_freeze),
        },
        "materialization_validation": {
            "valid": True,
            "materialized_cases": len(materialized),
            "gold_fields_in_model_context": 0,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "data_status": output["data_status"],
                "source_clusters": output["source_clusters"],
                "case_count": output["case_count"],
                "materialization_validation": output["materialization_validation"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_object(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


if __name__ == "__main__":
    main()
