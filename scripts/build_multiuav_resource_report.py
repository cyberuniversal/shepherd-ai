"""Build provenance-bound MultiUAV resource tables, figures, and report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_resource_reporting import (  # noqa: E402
    build_resource_report_artifacts,
    load_resource_report_data,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--summary", type=Path, default=None)
    parser.add_argument("--figure-dir", type=Path, default=None)
    parser.add_argument("--table-dir", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args()

    root = args.root.resolve()
    figure_dir = args.figure_dir or root / "reports" / "figures"
    table_dir = args.table_dir or root / "outputs" / "tables"
    report_path = args.report or root / "reports" / "multiuav_resource_results_v1.md"
    manifest_path = (
        args.manifest
        or root
        / "outputs"
        / "evaluations"
        / "multiuav_resource_reporting_v1"
        / "manifest.json"
    )
    report_data = load_resource_report_data(root, summary_path=args.summary)
    manifest = build_resource_report_artifacts(
        repository_root=root,
        report_data=report_data,
        figure_dir=figure_dir,
        table_dir=table_dir,
        report_path=report_path,
    )
    manifest["source_code_sha256"]["build_multiuav_resource_report.py"] = (
        _sha256_file(Path(__file__))
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    manifest_path.write_bytes(rendered.encode("utf-8"))
    print(rendered, end="")


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
