"""Render a static Week 8 demonstration screenshot from stored telemetry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulation", type=Path, required=True)
    parser.add_argument("--telemetry", type=Path, required=True)
    parser.add_argument("--map", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports/week8_demonstration.png",
    )
    args = parser.parse_args()
    import matplotlib.pyplot as plt

    simulation = json.loads(args.simulation.read_text(encoding="utf-8"))
    snapshots = [
        json.loads(line)
        for line in args.telemetry.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not snapshots:
        raise ValueError("telemetry contains no records")
    locations = load_map_locations(args.map)
    tracks: dict[str, tuple[list[float], list[float]]] = {}
    for snapshot in snapshots:
        for row in snapshot.get("drones", []):
            longitude, latitude = tracks.setdefault(str(row["drone_id"]), ([], []))
            longitude.append(float(row["longitude"]))
            latitude.append(float(row["latitude"]))

    fig, axis = plt.subplots(figsize=(16, 9), dpi=120)
    for location in locations:
        color = "#b2182b" if not location.flyable else "#6b7280"
        axis.scatter(location.longitude, location.latitude, s=60, color=color, zorder=2)
        axis.annotate(
            location.name,
            (location.longitude, location.latitude),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
            color="#30343b",
        )
    colors = ("#0072b2", "#d55e00", "#009e73")
    for index, (drone_id, (longitudes, latitudes)) in enumerate(sorted(tracks.items())):
        color = colors[index % len(colors)]
        axis.plot(longitudes, latitudes, color=color, linewidth=2.2, label=drone_id, zorder=3)
        axis.scatter(longitudes[0], latitudes[0], marker="o", s=45, color=color, zorder=4)
        axis.scatter(longitudes[-1], latitudes[-1], marker="s", s=45, color=color, zorder=4)
    result = simulation.get("simulation", {})
    axis.set_title(
        "Shepherd-AI Week 8 Software Simulation\n"
        f"status={result.get('status')} | assignments={result.get('assignment_count')} | "
        f"minimum separation={result.get('minimum_observed_separation_m')} m"
    )
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.grid(True, color="#d1d5db", linewidth=0.6)
    axis.legend(title="Simulated drones", loc="best")
    axis.set_aspect("equal", adjustable="datalim")
    fig.tight_layout()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps({"output": str(args.output), "telemetry_records": len(snapshots)}, indent=2))


if __name__ == "__main__":
    main()
