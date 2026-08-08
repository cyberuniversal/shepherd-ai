"""Admit sealed MultiUAV accuracy matrices without scoring study outcomes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_admission import (  # noqa: E402
    admit_accuracy_study,
)
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


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
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "datasets" / "multiuav_plat" / "accuracy_case_manifest_v1.json",
    )
    parser.add_argument(
        "--run-configs",
        type=Path,
        default=ROOT / "datasets" / "multiuav_plat" / "accuracy_run_configs_v1.json",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        action="append",
        help="Sealed checkpoint ZIP; repeat once per frozen model.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = admit_accuracy_study(
        manifest_path=args.manifest,
        run_configs_path=args.run_configs,
        checkpoint_paths=tuple(args.checkpoint or DEFAULT_CHECKPOINTS),
    )
    report["source_code_sha256"] = {
        "multiuav_admission.py": sha256_file(
            ROOT / "src" / "shepherd_ai" / "multiuav_admission.py"
        ),
        "multiuav_publication.py": sha256_file(
            ROOT / "src" / "shepherd_ai" / "multiuav_publication.py"
        ),
        "admit_multiuav_accuracy_matrices.py": sha256_file(Path(__file__)),
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
