"""Bind final accuracy run configs to a clean committed repository state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_evaluation_data import (  # noqa: E402
    build_accuracy_run_configs,
)
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "datasets" / "multiuav_plat" / "accuracy_case_manifest_v1.json",
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

    status = _git("status", "--porcelain")
    if status.strip():
        raise ValueError("final run configs require a clean committed worktree")
    code_commit = _git("rev-parse", "HEAD").strip().lower()
    manifest = _read_object(args.manifest)
    protocol = _read_object(args.protocol_freeze)
    protocol_hash = sha256_file(args.protocol_freeze)
    if manifest.get("artifact_bindings", {}).get("protocol_freeze_sha256") != (
        protocol_hash
    ):
        raise ValueError("accuracy manifest is not bound to the protocol freeze")
    configs = build_accuracy_run_configs(
        manifest,
        protocol,
        manifest_sha256=sha256_file(args.manifest),
        code_commit=code_commit,
    )
    output = {
        "schema_version": 1,
        "status": "final_accuracy_configs_bound_no_inference_started",
        "code_commit": code_commit,
        "accuracy_manifest_sha256": sha256_file(args.manifest),
        "protocol_freeze_sha256": protocol_hash,
        "expected_rows_per_model": manifest["case_count"] * len(protocol["methods"]),
        "expected_rows_total": protocol["expected_accuracy_rows"],
        "configs": [config.to_dict() for config in configs],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, sort_keys=True))


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _read_object(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


if __name__ == "__main__":
    main()
