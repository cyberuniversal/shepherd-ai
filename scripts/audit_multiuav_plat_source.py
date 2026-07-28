"""Verify the pinned MultiUAV-Plat source checkout and benchmark archive."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_source import (  # noqa: E402
    EXPECTED_ARCHIVE_SHA256,
    audit_benchmark_archive,
    sha256_file,
)


EXPECTED_COMMIT = "1794e45e421fb5de03094f0b63f9ca95f86ab42f"
EXPECTED_LICENSE_SHA256 = (
    "230184f60bae2feaf244f10a8bac053c8ff33a183bcc365b4d8b876d2b7f4809"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=ROOT / "external" / "MultiUAV-Plat",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repository = args.repository_root.resolve()
    commit = _git_output(repository, "rev-parse", "HEAD")
    if commit != EXPECTED_COMMIT:
        raise ValueError(
            f"source commit mismatch: expected {EXPECTED_COMMIT}, got {commit}"
        )

    archive = repository / "benchmark" / "benchmark.zip"
    license_path = repository / "LICENSE"
    if not license_path.is_file():
        raise ValueError(f"upstream LICENSE is missing: {license_path}")
    license_sha256 = sha256_file(license_path)
    if license_sha256 != EXPECTED_LICENSE_SHA256:
        raise ValueError(
            "upstream LICENSE SHA-256 mismatch: "
            f"expected {EXPECTED_LICENSE_SHA256}, got {license_sha256}"
        )
    license_heading = "\n".join(
        license_path.read_text(encoding="utf-8-sig").splitlines()[:2]
    )
    if "GNU GENERAL PUBLIC LICENSE" not in license_heading:
        raise ValueError("upstream LICENSE is not the audited GPL text")

    benchmark = audit_benchmark_archive(archive)
    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "repository": "https://github.com/zhangsheng93/MultiUAV-Plat",
            "commit": commit,
            "archive_relative_path": "benchmark/benchmark.zip",
            "archive_sha256": EXPECTED_ARCHIVE_SHA256,
            "license": "GPL-3.0",
            "license_sha256": license_sha256,
        },
        "benchmark": benchmark,
        "valid": True,
        "claim_status": "source_integrity_and_schema_audited_only",
        "limitations": [
            "No Shepherd-AI derivative cases were generated.",
            "No model was trained or evaluated.",
            "Static archive validation is not official-server mission execution.",
            "Instruction duplicates require split-overlap controls before generation.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def _git_output(repository: Path, *arguments: str) -> str:
    if not repository.is_dir():
        raise ValueError(f"source repository does not exist: {repository}")
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


if __name__ == "__main__":
    main()
