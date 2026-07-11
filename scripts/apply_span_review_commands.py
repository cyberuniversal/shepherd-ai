"""Apply reviewed span-label commands to a full span dataset safely."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REBUILD_SCRIPT = ROOT / "scripts" / "rebuild_span_dataset_from_commands.py"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_span_dataset.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commands-file", required=True, help="Reviewed command subset file.")
    parser.add_argument("--base-dataset", default="datasets/commands/human_verified_span_commands.jsonl")
    parser.add_argument("--output", default="datasets/commands/human_verified_span_commands.jsonl")
    parser.add_argument("--summary-output", default="outputs/evaluations/human_verified_span_commands_summary.json")
    parser.add_argument("--bio-output", default="outputs/evaluations/human_verified_span_commands_bio.jsonl")
    parser.add_argument("--no-backup", action="store_true", help="Do not back up an existing output file.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_dataset = Path(args.base_dataset)
    output = Path(args.output)
    with tempfile.TemporaryDirectory(prefix="shepherd_span_review_") as tmp:
        tmp_dir = Path(tmp)
        reviewed_subset = tmp_dir / "reviewed_subset.jsonl"
        _rebuild_review_subset(Path(args.commands_file), reviewed_subset, tmp_dir)
        base_records = _read_jsonl(base_dataset)
        reviewed_records = _read_jsonl(reviewed_subset)
        merged_records, replaced_ids = _merge_records(base_records, reviewed_records)

        temp_output = output.with_name(f"{output.name}.tmp-apply-review")
        temp_output.parent.mkdir(parents=True, exist_ok=True)
        _write_jsonl(temp_output, merged_records)
        _run_validation(temp_output, Path(args.summary_output), Path(args.bio_output))

        backup_path: Path | None = None
        if output.exists() and not args.no_backup:
            backup_path = _backup_path(output)
            shutil.copy2(output, backup_path)
        shutil.move(str(temp_output), output)

    summary = json.loads(Path(args.summary_output).read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "base_records": len(base_records),
                "reviewed_records": len(reviewed_records),
                "output_records": summary["records"],
                "replaced_ids": replaced_ids,
                "backup": str(backup_path) if backup_path else None,
                "output": str(output),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _rebuild_review_subset(commands_file: Path, output: Path, tmp_dir: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            str(REBUILD_SCRIPT),
            "--commands-file",
            str(commands_file),
            "--output",
            str(output),
            "--summary-output",
            str(tmp_dir / "reviewed_summary.json"),
            "--bio-output",
            str(tmp_dir / "reviewed_bio.jsonl"),
            "--no-backup",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8")


def _merge_records(
    base_records: list[dict[str, Any]], reviewed_records: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    _reject_duplicate_ids(base_records, "base dataset")
    _reject_duplicate_ids(reviewed_records, "reviewed subset")
    base_ids = {str(record["id"]) for record in base_records}
    reviewed_by_id = {str(record["id"]): record for record in reviewed_records}
    missing = sorted(set(reviewed_by_id) - base_ids)
    if missing:
        raise ValueError(f"reviewed ids not present in base dataset: {missing}")
    merged = [reviewed_by_id.get(str(record["id"]), record) for record in base_records]
    return merged, sorted(reviewed_by_id)


def _reject_duplicate_ids(records: list[dict[str, Any]], label: str) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for record in records:
        record_id = str(record.get("id"))
        if record_id in seen:
            duplicates.add(record_id)
        seen.add(record_id)
    if duplicates:
        raise ValueError(f"duplicate ids in {label}: {sorted(duplicates)}")


def _run_validation(dataset: Path, summary_output: Path, bio_output: Path) -> None:
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    bio_output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            str(VALIDATE_SCRIPT),
            "--dataset",
            str(dataset),
            "--summary-output",
            str(summary_output),
            "--bio-output",
            str(bio_output),
        ],
        cwd=ROOT,
        check=True,
    )


def _backup_path(output: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return output.with_name(f"{output.name}.bak-{stamp}")


if __name__ == "__main__":
    main()
