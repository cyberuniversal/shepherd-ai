"""Score admitted MultiUAV matrices under the frozen label-separated contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_study_scoring import score_admitted_study  # noqa: E402


DEFAULT_CHECKPOINTS = (
    ROOT
    / "datasets"
    / "multiuav_plat"
    / "nautilus"
    / "qwen25_3b_accuracy_complete_v1"
    / "checkpoint.zip",
    ROOT
    / "datasets"
    / "multiuav_plat"
    / "nautilus"
    / "qwen25_7b_accuracy_complete_v1"
    / "checkpoint.zip",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    metadata = ROOT / "datasets" / "multiuav_plat"
    parser.add_argument(
        "--admission",
        type=Path,
        default=metadata / "accuracy_matrix_admission_v1.json",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=metadata / "accuracy_case_manifest_v1.json",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=metadata / "intervention_dataset_v1.json",
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=metadata / "accuracy_protocol_freeze_v1.json",
    )
    parser.add_argument(
        "--run-configs",
        type=Path,
        default=metadata / "accuracy_run_configs_v1.json",
    )
    parser.add_argument(
        "--source-archive",
        type=Path,
        default=ROOT / "external" / "MultiUAV-Plat" / "benchmark" / "benchmark.zip",
    )
    parser.add_argument("--checkpoint", type=Path, action="append")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "outputs" / "evaluations" / "multiuav_accuracy_scoring_v1",
    )
    args = parser.parse_args()

    report = score_admitted_study(
        repository_root=ROOT,
        admission_path=args.admission,
        manifest_path=args.manifest,
        dataset_path=args.dataset,
        protocol_path=args.protocol,
        run_configs_path=args.run_configs,
        source_archive_path=args.source_archive,
        checkpoint_paths=tuple(args.checkpoint or DEFAULT_CHECKPOINTS),
        output_dir=args.output_dir,
    )
    output = args.output_dir / "summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
