"""Run the registered MultiUAV source-cluster bootstrap analysis."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_study_analysis import analyze_scored_study  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--intervention-dataset",
        type=Path,
        default=ROOT
        / "datasets"
        / "multiuav_plat"
        / "intervention_dataset_v1.json",
    )
    parser.add_argument(
        "--scoring-summary",
        type=Path,
        default=ROOT
        / "outputs"
        / "evaluations"
        / "multiuav_accuracy_scoring_v1"
        / "summary.json",
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT
        / "datasets"
        / "multiuav_plat"
        / "accuracy_protocol_freeze_v1.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT
        / "outputs"
        / "evaluations"
        / "multiuav_accuracy_bootstrap_v1",
    )
    parser.add_argument(
        "--session-statistics-output",
        type=Path,
        default=ROOT
        / "outputs"
        / "tables"
        / "multiuav_accuracy_session_statistics_v1.csv",
    )
    parser.add_argument(
        "--failure-analysis-output",
        type=Path,
        default=ROOT
        / "outputs"
        / "evaluations"
        / "multiuav_accuracy_failure_analysis_v1.json",
    )
    parser.add_argument(
        "--failure-cases-output",
        type=Path,
        default=ROOT
        / "outputs"
        / "evaluations"
        / "multiuav_accuracy_failure_cases_v1.zip",
    )
    args = parser.parse_args()

    report = analyze_scored_study(
        repository_root=ROOT,
        scoring_summary_path=args.scoring_summary,
        protocol_path=args.protocol,
        intervention_dataset_path=args.intervention_dataset,
        output_dir=args.output_dir,
    )
    session_rows = report["descriptive_session_statistics"].pop("session_rows")
    failure_cases = report["descriptive_failure_analysis"].pop("failure_case_rows")
    _write_csv(args.session_statistics_output, session_rows)
    session_record = _file_record(args.session_statistics_output)
    report["descriptive_session_statistics"]["session_table"] = session_record

    failure_payload = {
        "schema_version": 1,
        **report["descriptive_failure_analysis"],
    }
    _write_json(args.failure_analysis_output, failure_payload)
    failure_analysis_record = _file_record(args.failure_analysis_output)
    failure_cases_record = _write_failure_archive(
        args.failure_cases_output,
        failure_cases,
        metadata={
            "schema_version": 1,
            "analysis_status": "post_hoc_descriptive_no_inference",
            "raw_model_text_included": False,
        },
    )
    report["descriptive_failure_analysis"] = {
        **failure_payload,
        "failure_analysis": failure_analysis_record,
        "failure_cases_archive": failure_cases_record,
    }
    output = args.output_dir / "summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("session statistics are empty")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_failure_archive(path: Path, rows: list[dict], metadata: dict) -> dict:
    row_bytes = b"".join(
        (json.dumps(row, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")
        for row in rows
    )
    metadata_bytes = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8")
    manifest = {
        "schema_version": 1,
        "failure_rows": len(rows),
        "files": {
            "failure_cases.jsonl": _content_record(row_bytes),
            "metadata.json": _content_record(metadata_bytes),
        },
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted({
            "failure_cases.jsonl": row_bytes,
            "manifest.json": manifest_bytes,
            "metadata.json": metadata_bytes,
        }.items()):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)
    temporary.replace(path)
    return {"path": path.relative_to(ROOT).as_posix(), "failure_rows": len(rows), **_file_record(path)}


def _content_record(content: bytes) -> dict:
    return {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}


def _file_record(path: Path) -> dict:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    main()
