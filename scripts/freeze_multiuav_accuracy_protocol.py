"""Freeze score-blind MultiUAV accuracy estimands before study inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_protocol import (  # noqa: E402
    build_accuracy_protocol_freeze,
)
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    dataset_validation = _read_object(args.dataset_validation)
    expert_qc = _read_object(args.expert_qc)
    protocol = build_accuracy_protocol_freeze(dataset_validation, expert_qc)
    output = {
        "schema_version": 1,
        **protocol,
        "artifact_bindings": {
            "dataset_validation_sha256": sha256_file(args.dataset_validation),
            "expert_qc_sha256": sha256_file(args.expert_qc),
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
