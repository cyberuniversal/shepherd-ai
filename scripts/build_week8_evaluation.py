"""Build Week 8 metrics, mission report, and demonstration log from raw evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week8_evaluation import (  # noqa: E402
    build_week8_end_to_end_evaluation,
    render_week8_demonstration_log,
    render_week8_mission_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulation", type=Path, required=True)
    parser.add_argument("--asr-evidence", type=Path, required=True)
    parser.add_argument("--intent-evaluation", type=Path, required=True)
    parser.add_argument("--vision-evaluation", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "outputs/evaluations/week8_end_to_end_evaluation.json",
    )
    parser.add_argument(
        "--mission-report",
        type=Path,
        default=ROOT / "reports/week8_mission_report.md",
    )
    parser.add_argument(
        "--demonstration-log",
        type=Path,
        default=ROOT / "reports/week8_demonstration.log",
    )
    args = parser.parse_args()
    simulation = _read_json(args.simulation)
    result = build_week8_end_to_end_evaluation(
        simulation=simulation,
        asr_evidence=_read_json(args.asr_evidence),
        intent_evaluation=_read_json(args.intent_evaluation),
        vision_evaluation=_read_json(args.vision_evaluation),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.mission_report.parent.mkdir(parents=True, exist_ok=True)
    args.mission_report.write_text(render_week8_mission_report(result), encoding="utf-8")
    args.demonstration_log.parent.mkdir(parents=True, exist_ok=True)
    args.demonstration_log.write_text(
        render_week8_demonstration_log(simulation, result), encoding="utf-8"
    )
    print(json.dumps({"status": result["status"], "metrics": result["metrics"]}, indent=2))


def _read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


if __name__ == "__main__":
    main()
