"""Store rejection evidence for synthetic intervention-validator probes."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_interventions import (  # noqa: E402
    run_validator_negative_controls,
)
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "datasets" / "multiuav_plat" / "intervention_pilot_v2.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    results = run_validator_negative_controls(dataset)
    output = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "pilot_dataset_sha256": sha256_file(args.dataset),
        "probes": results,
        "summary": {
            "probe_count": len(results),
            "expected_rejections": len(results),
            "observed_rejections": sum(
                result["observed"] == "rejected" for result in results
            ),
        },
        "claim_status": "synthetic_validator_negative_controls_not_study_data",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
