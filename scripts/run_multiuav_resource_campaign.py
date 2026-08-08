"""Run all frozen resource conditions in registered order as isolated processes."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    metadata = ROOT / "datasets/multiuav_plat"
    parser.add_argument(
        "--run-configs", type=Path, default=metadata / "resource_run_configs_v1.json"
    )
    parser.add_argument(
        "--schedule", type=Path, default=metadata / "resource_schedule_v1.json"
    )
    parser.add_argument(
        "--hardware-protocol",
        type=Path,
        default=metadata / "resource_hardware_protocol_v1.json",
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--node-name", required=True)
    parser.add_argument("--cache-audit-root", type=Path, default=metadata)
    args = parser.parse_args()

    schedule = _read(args.schedule)
    rows = sorted(
        schedule["condition_schedule"]["rows"],
        key=lambda row: (int(row["repetition"]), int(row["condition_order"])),
    )
    args.output_root.mkdir(parents=True, exist_ok=True)
    campaign_summary = args.output_root / "campaign_summary.json"
    completed: list[dict] = []
    for row in rows:
        repetition = int(row["repetition"])
        order = int(row["condition_order"])
        condition = args.output_root / f"r{repetition}-o{order}"
        condition.mkdir(parents=True, exist_ok=True)
        summary_path = condition / "run_summary.json"
        if summary_path.exists() and _read(summary_path).get("status") == (
            "complete_valid_resource_condition"
        ):
            completed.append({"repetition": repetition, "condition_order": order})
            _write_campaign(campaign_summary, completed, total=len(rows))
            continue
        slug = "3b" if "3B" in str(row["model_id"]) else "7b"
        command = [
            sys.executable,
            str(ROOT / "scripts/run_multiuav_resource.py"),
            "--run-configs",
            str(args.run_configs),
            "--schedule",
            str(args.schedule),
            "--hardware-protocol",
            str(args.hardware_protocol),
            "--repetition",
            str(repetition),
            "--condition-order",
            str(order),
            "--cache-audit",
            str(args.cache_audit_root / f"qwen25_{slug}_cache_audit_nautilus_v1.json"),
            "--smoke-audit",
            str(args.cache_audit_root / f"qwen25_{slug}_load_smoke_nautilus_v1.json"),
            "--results",
            str(condition / "results.jsonl"),
            "--checkpoint-zip",
            str(condition / "checkpoint.zip"),
            "--run-summary",
            str(summary_path),
            "--start-control-dir",
            str(condition / "start_controls"),
            "--hardware-lock",
            str(args.output_root / "hardware_lock.json"),
            "--node-name",
            args.node_name,
        ]
        try:
            with (condition / "stdout.log").open("a", encoding="utf-8") as stdout, (
                condition / "stderr.log"
            ).open("a", encoding="utf-8") as stderr:
                subprocess.run(
                    command,
                    cwd=ROOT,
                    check=True,
                    stdout=stdout,
                    stderr=stderr,
                )
        except subprocess.CalledProcessError as error:
            _write_campaign(
                campaign_summary,
                completed,
                total=len(rows),
                failure={
                    "repetition": repetition,
                    "condition_order": order,
                    "returncode": error.returncode,
                    "condition_directory": condition.as_posix(),
                },
            )
            raise
        completed.append({"repetition": repetition, "condition_order": order})
        _write_campaign(campaign_summary, completed, total=len(rows))
    _write_campaign(campaign_summary, completed, total=len(rows), complete=True)


def _write_campaign(
    path: Path,
    completed: list[dict],
    *,
    total: int,
    complete: bool = False,
    failure: dict | None = None,
) -> None:
    payload = {
        "schema_version": 1,
        "status": (
            "resource_campaign_failed_raw_results_preserved"
            if failure is not None
            else "complete_resource_campaign_raw_results_unscored"
            if complete
            else "resource_campaign_in_progress"
        ),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "completed_conditions": completed,
        "completed_condition_count": len(completed),
        "expected_conditions": total,
        "raw_model_outputs_inspected": False,
        "resource_scores_computed": False,
    }
    if failure is not None:
        payload["failed_condition"] = failure
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


if __name__ == "__main__":
    main()
