"""Deterministic time-stepped execution for the Shepherd-AI software simulation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import cos, pi, radians, sin
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable, Mapping

import folium
from folium.plugins import TimestampedGeoJson

from shepherd_ai.grounding import MapLocation
from shepherd_ai.mission_supervision import MissionSupervisor
from shepherd_ai.safety import SafetyPolicy, validate_inter_drone_separation
from shepherd_ai.scheduling import Assignment, DroneState, ScheduleResult


SIMULATOR_NAME = "deterministic_2d_mission_simulator_v1"
_DRONE_COLORS = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00")


def schedule_from_payload(payload: Mapping[str, Any]) -> ScheduleResult:
    """Reconstruct a validated scheduler result from a stored payload."""

    assignments = tuple(Assignment(**row) for row in payload.get("assignments", []))
    return ScheduleResult(
        strategy=str(payload.get("strategy", "")),
        assignments=assignments,
        unassigned_tasks=tuple(str(value) for value in payload.get("unassigned_tasks", [])),
        metrics=dict(payload.get("metrics", {})),
        notes=tuple(str(value) for value in payload.get("notes", [])),
    )


def simulate_schedule(
    schedule: ScheduleResult,
    drones: Iterable[DroneState],
    locations: Iterable[MapLocation],
    safety_policy: SafetyPolicy,
    *,
    time_step_min: float = 0.25,
) -> dict[str, Any]:
    """Execute scheduled round trips as explicit 2D simulated telemetry."""

    if time_step_min <= 0.0:
        raise ValueError("time_step_min must be positive")
    if not schedule.assignments:
        raise ValueError("simulation requires at least one assignment")
    if schedule.unassigned_tasks:
        raise ValueError("simulation cannot start with unassigned tasks")

    started = perf_counter()
    drone_tuple = tuple(drones)
    drone_index = {drone.drone_id: drone for drone in drone_tuple}
    location_index = {location.id: location for location in locations}
    missing_drones = sorted({row.drone_id for row in schedule.assignments} - set(drone_index))
    missing_locations = sorted(
        {row.target_location_id for row in schedule.assignments} - set(location_index)
    )
    if missing_drones:
        raise ValueError(f"schedule references unknown drones: {', '.join(missing_drones)}")
    if missing_locations:
        raise ValueError(f"schedule references unknown locations: {', '.join(missing_locations)}")

    task_slots = _formation_slots(schedule.assignments, location_index, safety_policy)
    makespan = max(assignment.end_min for assignment in schedule.assignments)
    times = _simulation_times(makespan, time_step_min)
    snapshots: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    previous_phases: dict[str, str] = {}
    minimum_observed = float("inf")
    status = "completed"
    completed_tasks: set[str] = set()
    supervisor = MissionSupervisor(
        schedule,
        drone_tuple,
        location_index,
        safety_policy,
        mission_altitude_m=safety_policy.default_mission_altitude_m,
    )
    supervisor.confirm_and_start(drone_tuple)
    if supervisor.snapshot()["mission_status"] != "active":
        raise ValueError("simulation supervisor blocked initial preflight")

    for snapshot_index, time_min in enumerate(times):
        drone_rows: list[dict[str, Any]] = []
        states: list[DroneState] = []
        for drone_id in sorted(drone_index):
            drone = drone_index[drone_id]
            row = _drone_at_time(
                drone,
                schedule.assignments,
                task_slots,
                time_min,
                safety_policy.default_mission_altitude_m,
            )
            drone_rows.append(row)
            states.append(
                DroneState(
                    drone_id=drone.drone_id,
                    status="idle",
                    current_location_id=str(row["location_reference_id"]),
                    current_latitude=float(row["latitude"]),
                    current_longitude=float(row["longitude"]),
                    available_at_min=time_min,
                    battery_percent=drone.battery_percent,
                    speed_m_per_min=drone.speed_m_per_min,
                    notes=("time_stepped_simulated_telemetry",),
                )
            )
            phase = str(row["phase"])
            if previous_phases.get(drone_id) != phase:
                events.append(
                    {
                        "time_min": round(time_min, 6),
                        "event": "phase_changed",
                        "drone_id": drone_id,
                        "task_id": row["task_id"],
                        "phase": phase,
                    }
                )
                previous_phases[drone_id] = phase

        separation = validate_inter_drone_separation(states, safety_policy)
        pair_distances = separation.evidence.get("pair_distances", [])
        if pair_distances:
            minimum_observed = min(
                minimum_observed,
                min(float(pair["distance_m"]) for pair in pair_distances),
            )
        snapshots.append(
            {
                "time_min": round(time_min, 6),
                "drones": drone_rows,
                "separation_check": separation.to_dict(),
            }
        )
        if snapshot_index > 0 and supervisor.snapshot()["mission_status"] in {"active", "paused"}:
            supervisor.apply_telemetry(states)
        for assignment in schedule.assignments:
            if (
                assignment.task_id not in completed_tasks
                and time_min >= assignment.end_min
                and supervisor.snapshot()["mission_status"] == "active"
            ):
                supervisor.complete_task(assignment.task_id)
                completed_tasks.add(assignment.task_id)
        if separation.status != "passed":
            status = "runtime_safety_violation"
            events.append(
                {
                    "time_min": round(time_min, 6),
                    "event": "safety_hold",
                    "category": separation.category,
                    "reason": separation.reason,
                    "evidence": separation.evidence,
                }
            )
            break

    if minimum_observed == float("inf"):
        minimum_observed = 0.0
    return {
        "status": status,
        "simulator": SIMULATOR_NAME,
        "strategy": schedule.strategy,
        "assignment_count": len(schedule.assignments),
        "time_step_min": time_step_min,
        "planned_makespan_min": makespan,
        "simulated_until_min": snapshots[-1]["time_min"],
        "minimum_required_separation_m": safety_policy.minimum_inter_drone_separation_m,
        "minimum_observed_separation_m": round(minimum_observed, 6),
        "task_slots": task_slots,
        "events": events,
        "supervision": supervisor.snapshot(),
        "snapshots": snapshots,
        "wall_clock_seconds": perf_counter() - started,
        "limitations": [
            "Deterministic 2D kinematic interpolation; no aerodynamic or flight-controller dynamics.",
            "Formation slots are static geometric deconfliction, not active collision avoidance.",
            "Battery percentage is held constant because no battery-consumption model is specified.",
            "Imagery capture and model inference are separate Week 8 stage artifacts.",
        ],
    }


def render_simulation_map(
    simulation: Mapping[str, Any],
    locations: Iterable[MapLocation],
    output: str | Path,
) -> Path:
    """Render time-stamped drone telemetry as an animated Folium map."""

    location_list = tuple(locations)
    if not location_list:
        raise ValueError("at least one map location is required")
    center = [
        sum(location.latitude for location in location_list) / len(location_list),
        sum(location.longitude for location in location_list) / len(location_list),
    ]
    map_view = folium.Map(location=center, zoom_start=16, control_scale=True)
    for location in location_list:
        color = "#B2182B" if not location.flyable else "#666666"
        folium.Circle(
            location=[location.latitude, location.longitude],
            radius=location.radius_m,
            color=color,
            fill=True,
            fill_opacity=0.06,
            weight=1,
            tooltip=f"{location.name} ({location.id})",
        ).add_to(map_view)

    features: list[dict[str, Any]] = []
    snapshots = list(simulation.get("snapshots", []))
    drone_ids = sorted(
        {str(row["drone_id"]) for snapshot in snapshots for row in snapshot.get("drones", [])}
    )
    color_by_drone = {
        drone_id: _DRONE_COLORS[index % len(_DRONE_COLORS)]
        for index, drone_id in enumerate(drone_ids)
    }
    base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for snapshot in snapshots:
        timestamp = (base_time + timedelta(minutes=float(snapshot["time_min"]))).isoformat()
        for row in snapshot.get("drones", []):
            drone_id = str(row["drone_id"])
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(row["longitude"]), float(row["latitude"])],
                    },
                    "properties": {
                        "time": timestamp,
                        "popup": (
                            f"{drone_id}<br>phase={row['phase']}<br>"
                            f"task={row.get('task_id') or 'none'}<br>t={snapshot['time_min']} min"
                        ),
                        "icon": "circle",
                        "iconstyle": {
                            "fillColor": color_by_drone[drone_id],
                            "fillOpacity": 0.9,
                            "stroke": True,
                            "color": "#111111",
                            "weight": 1,
                            "radius": 6,
                        },
                    },
                }
            )
    period_seconds = max(1, int(round(float(simulation["time_step_min"]) * 60.0)))
    TimestampedGeoJson(
        {"type": "FeatureCollection", "features": features},
        period=f"PT{period_seconds}S",
        duration=f"PT{period_seconds}S",
        auto_play=False,
        loop=False,
        add_last_point=True,
        time_slider_drag_update=True,
    ).add_to(map_view)
    folium.LayerControl().add_to(map_view)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    map_view.save(str(output_path))
    rendered = output_path.read_text(encoding="utf-8")
    output_path.write_text(
        "\n".join(line.rstrip() for line in rendered.splitlines()) + "\n",
        encoding="utf-8",
    )
    return output_path


def _formation_slots(
    assignments: Iterable[Assignment],
    locations: Mapping[str, MapLocation],
    policy: SafetyPolicy,
) -> dict[str, dict[str, Any]]:
    by_target: dict[str, list[Assignment]] = {}
    for assignment in assignments:
        by_target.setdefault(assignment.target_location_id, []).append(assignment)
    slots: dict[str, dict[str, Any]] = {}
    for location_id, target_assignments in sorted(by_target.items()):
        location = locations[location_id]
        rows = sorted(target_assignments, key=lambda value: value.task_id)
        if len(rows) == 1:
            offsets = [(0.0, 0.0)]
        else:
            slot_radius = min(
                max(policy.minimum_inter_drone_separation_m, 10.0),
                max(location.radius_m * 0.5, 10.0),
            )
            offsets = [
                (
                    slot_radius * cos(2.0 * pi * index / len(rows)),
                    slot_radius * sin(2.0 * pi * index / len(rows)),
                )
                for index in range(len(rows))
            ]
        for assignment, (east_m, north_m) in zip(rows, offsets):
            latitude = location.latitude + north_m / 111_320.0
            longitude = location.longitude + east_m / (
                111_320.0 * max(cos(radians(location.latitude)), 0.01)
            )
            slots[assignment.task_id] = {
                "target_location_id": location_id,
                "target_name": location.name,
                "latitude": latitude,
                "longitude": longitude,
                "east_offset_m": east_m,
                "north_offset_m": north_m,
            }
    return slots


def _simulation_times(makespan: float, time_step_min: float) -> list[float]:
    count = int(makespan // time_step_min)
    times = [index * time_step_min for index in range(count + 1)]
    if not times or abs(times[-1] - makespan) > 1e-9:
        times.append(makespan)
    return times


def _drone_at_time(
    drone: DroneState,
    assignments: Iterable[Assignment],
    task_slots: Mapping[str, Mapping[str, Any]],
    time_min: float,
    mission_altitude_m: float,
) -> dict[str, Any]:
    assigned = sorted(
        (row for row in assignments if row.drone_id == drone.drone_id),
        key=lambda row: (row.start_min, row.task_id),
    )
    active = next(
        (row for row in assigned if row.start_min <= time_min < row.end_min),
        None,
    )
    if active is None:
        all_complete = bool(assigned) and time_min >= max(row.end_min for row in assigned)
        return {
            "drone_id": drone.drone_id,
            "task_id": None,
            "phase": "completed" if all_complete else "waiting",
            "latitude": drone.current_latitude,
            "longitude": drone.current_longitude,
            "altitude_m": 0.0,
            "location_reference_id": drone.current_location_id,
        }

    slot = task_slots[active.task_id]
    one_way_min = (active.travel_distance_m / 2.0) / max(drone.speed_m_per_min, 1.0)
    work_min = max(active.duration_min - 2.0 * one_way_min, 0.0)
    elapsed = time_min - active.start_min
    if elapsed < one_way_min:
        fraction = elapsed / max(one_way_min, 1e-9)
        phase = "outbound"
        latitude = _interpolate(drone.current_latitude, float(slot["latitude"]), fraction)
        longitude = _interpolate(drone.current_longitude, float(slot["longitude"]), fraction)
    elif elapsed < one_way_min + work_min:
        phase = "on_station"
        latitude = float(slot["latitude"])
        longitude = float(slot["longitude"])
    else:
        fraction = (elapsed - one_way_min - work_min) / max(one_way_min, 1e-9)
        phase = "returning"
        latitude = _interpolate(float(slot["latitude"]), drone.current_latitude, fraction)
        longitude = _interpolate(float(slot["longitude"]), drone.current_longitude, fraction)
    return {
        "drone_id": drone.drone_id,
        "task_id": active.task_id,
        "phase": phase,
        "latitude": latitude,
        "longitude": longitude,
        "altitude_m": mission_altitude_m,
        "location_reference_id": active.target_location_id,
    }


def _interpolate(start: float, end: float, fraction: float) -> float:
    bounded = min(max(fraction, 0.0), 1.0)
    return start + (end - start) * bounded
