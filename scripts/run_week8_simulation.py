"""Run the resolved Week 8 three-drone software simulation and store artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations  # noqa: E402
from shepherd_ai.mission_simulation import (  # noqa: E402
    render_simulation_map,
    schedule_from_payload,
    simulate_schedule,
)
from shepherd_ai.safety import load_safety_policy  # noqa: E402
from shepherd_ai.scheduling import load_drones  # noqa: E402
from shepherd_ai.week8_pipeline import prepare_week8_mission  # noqa: E402


ROADMAP_COMMAND = (
    "Send two drones north to inspect crops and one drone east to inspect irrigation."
)
DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_FLEET = ROOT / "datasets" / "drones" / "week5_three_drone_fleet_v1.json"
DEFAULT_POLICY = ROOT / "datasets" / "safety" / "week7_safety_policy_v1.json"
DEFAULT_RESOLUTION = {"clause_002": "loc_east_field"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", default=ROADMAP_COMMAND)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--fleet", type=Path, default=DEFAULT_FLEET)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--strategy", default="least_loaded")
    parser.add_argument("--time-step-min", type=float, default=0.25)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--telemetry-output", type=Path, required=True)
    parser.add_argument("--map-output", type=Path, required=True)
    args = parser.parse_args()

    locations = load_map_locations(args.map)
    location_index = {location.id: location for location in locations}
    fleet = _read_json(args.fleet)
    policy = load_safety_policy(args.policy)
    preparation = prepare_week8_mission(
        args.command,
        locations=locations,
        fleet_payload=fleet,
        safety_policy=policy,
        strategy=args.strategy,
        grounding_resolutions=DEFAULT_RESOLUTION,
    )
    if preparation.get("schedule") is None or preparation.get("safety_report", {}).get("status") != "approved":
        raise RuntimeError(
            f"Week 8 simulation cannot start from preparation status: {preparation['status']}"
        )

    simulation = simulate_schedule(
        schedule_from_payload(preparation["schedule"]),
        load_drones(fleet, location_index),
        locations,
        policy,
        time_step_min=args.time_step_min,
    )
    _write_telemetry(args.telemetry_output, simulation["snapshots"])
    render_simulation_map(simulation, locations, args.map_output)
    simulation_summary = {key: value for key, value in simulation.items() if key != "snapshots"}
    simulation_summary["telemetry_output"] = _repo_path(args.telemetry_output)
    simulation_summary["telemetry_records"] = len(simulation["snapshots"])
    simulation_summary["animated_map_output"] = _repo_path(args.map_output)
    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "scenario_source": "roadmap_week8_fixed_scenario",
            "input_mode": "typed_development",
            "destination_resolution": DEFAULT_RESOLUTION,
            "destination_resolution_source": "explicit_operator_confirmation",
            "map": _repo_path(args.map),
            "fleet": _repo_path(args.fleet),
            "policy": _repo_path(args.policy),
            "strategy": args.strategy,
            "python_version": platform.python_version(),
            "package_versions": {
                "shepherd-ai": _package_version("shepherd-ai"),
                "folium": _package_version("folium"),
                "networkx": _package_version("networkx"),
            },
            "random_seed": None,
            "command_sha256": hashlib.sha256(args.command.encode("utf-8")).hexdigest(),
            "input_sha256": {
                "map": _sha256(args.map),
                "fleet": _sha256(args.fleet),
                "policy": _sha256(args.policy),
            },
            "research_note": (
                "Resolved typed-command software simulation. This is movement/supervision evidence, "
                "not complete Week 8 success because exact-scenario ASR and mission vision evidence "
                "are still missing."
            ),
            "artifact_sha256": {
                "telemetry": _sha256(args.telemetry_output),
                "animated_map": _sha256(args.map_output),
            },
        },
        "preparation": preparation,
        "simulation": simulation_summary,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": simulation["status"],
                "simulated_minutes": simulation["simulated_until_min"],
                "telemetry_records": len(simulation["snapshots"]),
                "minimum_observed_separation_m": simulation["minimum_observed_separation_m"],
                "output": str(args.output),
                "map_output": str(args.map_output),
            },
            indent=2,
        )
    )


def _write_telemetry(path: Path, snapshots: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(snapshot, sort_keys=True) + "\n" for snapshot in snapshots),
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
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


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not_installed"


if __name__ == "__main__":
    main()
