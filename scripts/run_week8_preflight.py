"""Run and store Week 8 compound-mission preparation evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations  # noqa: E402
from shepherd_ai.safety import load_safety_policy  # noqa: E402
from shepherd_ai.week8_pipeline import prepare_week8_mission  # noqa: E402


ROADMAP_COMMAND = (
    "Send two drones north to inspect crops and one drone east to inspect irrigation."
)
DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_FLEET = ROOT / "datasets" / "drones" / "week5_three_drone_fleet_v1.json"
DEFAULT_POLICY = ROOT / "datasets" / "safety" / "week7_safety_policy_v1.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", default=ROADMAP_COMMAND)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--fleet", type=Path, default=DEFAULT_FLEET)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--strategy", default="least_loaded")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = prepare_week8_mission(
        args.command,
        locations=load_map_locations(args.map),
        fleet_payload=_read_json(args.fleet),
        safety_policy=load_safety_policy(args.policy),
        strategy=args.strategy,
    )
    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "scenario_source": "roadmap_week8_fixed_scenario",
            "input_mode": "typed_development",
            "map": _repo_path(args.map),
            "fleet": _repo_path(args.fleet),
            "policy": _repo_path(args.policy),
            "strategy": args.strategy,
            "python_version": platform.python_version(),
            "random_seed": None,
            "input_sha256": {
                "map": _sha256(args.map),
                "fleet": _sha256(args.fleet),
                "policy": _sha256(args.policy),
            },
            "research_note": (
                "Typed Week 8 preparation evidence only. A blocked result is retained as a "
                "negative result and is not end-to-end mission success."
            ),
        },
        "pipeline_result": result,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output)}, indent=2))


def _read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON input must contain an object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return str(resolved)


if __name__ == "__main__":
    main()
