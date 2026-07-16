"""Run one bounded Week 7 workflow and store its complete JSON result."""

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
from shepherd_ai.integration import run_integrated_workflow  # noqa: E402
from shepherd_ai.safety import load_safety_policy  # noqa: E402


DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_FLEET = ROOT / "datasets" / "drones" / "week5_three_drone_fleet_v1.json"
DEFAULT_POLICY = ROOT / "datasets" / "safety" / "week7_safety_policy_v1.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", required=True)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--fleet", type=Path, default=DEFAULT_FLEET)
    parser.add_argument("--current-fleet", type=Path)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--strategy", default="least_loaded")
    parser.add_argument("--altitude-m", type=float)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    fleet = _read_json(args.fleet)
    current_fleet = _read_json(args.current_fleet) if args.current_fleet else None
    result = run_integrated_workflow(
        args.command,
        locations=load_map_locations(args.map),
        fleet_payload=fleet,
        current_fleet_payload=current_fleet,
        safety_policy=load_safety_policy(args.policy),
        strategy=args.strategy,
        mission_altitude_m=args.altitude_m,
    )
    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "map": str(args.map),
            "scheduling_fleet": str(args.fleet),
            "current_fleet": str(args.current_fleet) if args.current_fleet else str(args.fleet),
            "policy": str(args.policy),
            "strategy": args.strategy,
            "python_version": platform.python_version(),
            "random_seed": None,
            "input_sha256": {
                "map": _sha256(args.map),
                "scheduling_fleet": _sha256(args.fleet),
                "current_fleet": _sha256(args.current_fleet or args.fleet),
                "policy": _sha256(args.policy),
            },
            "research_note": (
                "Week 7 pre-execution simulation result. It is not physical-flight execution, "
                "a safety guarantee, or an end-to-end Week 8 result."
            ),
        },
        "workflow_result": result.to_dict(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result.status, "output": str(args.output)}, indent=2, sort_keys=True))


def _read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON input must contain an object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    main()
