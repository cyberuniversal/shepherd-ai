"""Deterministic Week 5 scheduling for simulated drone assignments.

This module consumes Week 4 mission plans and simulated drone states. It
compares simple classical allocation baselines; it does not execute missions,
avoid collisions, validate safety, or control physical drones.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import atan2, cos, radians, sin, sqrt
from typing import Any, Iterable, Mapping


OBSERVATION_STEP_ACTIONS = {
    "capture_images",
    "inspect_area",
    "run_vision_model",
    "save_observation_results",
    "scan_area",
    "search_area",
}


@dataclass(frozen=True)
class DroneState:
    """One simulated drone available to the Week 5 scheduler."""

    drone_id: str
    status: str
    current_location_id: str
    current_latitude: float
    current_longitude: float
    available_at_min: float
    battery_percent: float
    speed_m_per_min: float
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["notes"] = list(self.notes)
        return payload


@dataclass(frozen=True)
class SchedulableTask:
    """One schedulable mission task derived from a Week 4 mission plan."""

    task_id: str
    source_plan_id: str
    action: str
    target_location_id: str
    target_name: str
    target_latitude: float
    target_longitude: float
    required_drone_index: int
    estimated_work_min: float
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["notes"] = list(self.notes)
        return payload


@dataclass(frozen=True)
class Assignment:
    """One assigned task in a simulated schedule."""

    task_id: str
    drone_id: str
    strategy: str
    start_min: float
    end_min: float
    duration_min: float
    travel_distance_m: float
    target_location_id: str
    target_name: str
    action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScheduleResult:
    """Assignment table and metrics for one scheduling strategy."""

    strategy: str
    assignments: tuple[Assignment, ...]
    unassigned_tasks: tuple[str, ...]
    metrics: dict[str, Any]
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "assignments": [assignment.to_dict() for assignment in self.assignments],
            "unassigned_tasks": list(self.unassigned_tasks),
            "metrics": self.metrics,
            "notes": list(self.notes),
        }


def load_drones(payload: Mapping[str, Any], map_locations: Mapping[str, Any]) -> tuple[DroneState, ...]:
    """Load simulated drone states from a JSON-compatible payload."""

    drones_payload = payload.get("drones", [])
    if not isinstance(drones_payload, list) or not drones_payload:
        raise ValueError("drone payload must contain a non-empty drones list")
    drones: list[DroneState] = []
    for row in drones_payload:
        if not isinstance(row, Mapping):
            raise ValueError("each drone must be an object")
        location_id = str(row.get("current_location_id") or row.get("home_location_id") or "")
        location = map_locations.get(location_id)
        if location is None:
            raise ValueError(f"unknown drone location_id: {location_id}")
        drones.append(
            DroneState(
                drone_id=str(row["drone_id"]),
                status=str(row.get("status", "idle")),
                current_location_id=location_id,
                current_latitude=float(location.latitude),
                current_longitude=float(location.longitude),
                available_at_min=float(row.get("available_at_min", 0.0)),
                battery_percent=float(row.get("battery_percent", 100.0)),
                speed_m_per_min=float(row.get("speed_m_per_min", 300.0)),
                notes=tuple(str(note) for note in row.get("notes", [])),
            )
        )
    return tuple(drones)


def extract_tasks_from_plan_payloads(plan_payloads: Iterable[Mapping[str, Any]]) -> tuple[SchedulableTask, ...]:
    """Create schedulable task replicas from Week 4 planning artifacts."""

    tasks: list[SchedulableTask] = []
    for plan_index, payload in enumerate(plan_payloads, start=1):
        plan = payload.get("mission_plan", payload)
        if not isinstance(plan, Mapping):
            raise ValueError("mission plan payload must be an object")
        if plan.get("status") != "planned" or plan.get("ready_for_scheduling") is not True:
            continue
        primary = plan.get("primary_map_object")
        intent = plan.get("intent", {})
        if not isinstance(primary, Mapping) or not isinstance(intent, Mapping):
            continue
        center = primary.get("center", {})
        if not isinstance(center, Mapping):
            continue
        count = _positive_count(intent.get("count"))
        base_task_id = f"mission_{plan_index:03d}"
        for required_index in range(1, count + 1):
            suffix = f"_drone_{required_index:02d}" if count > 1 else ""
            tasks.append(
                SchedulableTask(
                    task_id=f"{base_task_id}{suffix}",
                    source_plan_id=base_task_id,
                    action=str(intent.get("action") or "inspect"),
                    target_location_id=str(primary.get("location_id")),
                    target_name=str(primary.get("name")),
                    target_latitude=float(center.get("latitude")),
                    target_longitude=float(center.get("longitude")),
                    required_drone_index=required_index,
                    estimated_work_min=_estimate_work_minutes(plan),
                    notes=tuple(str(issue) for issue in plan.get("issues", [])),
                )
            )
    if not tasks:
        raise ValueError("no schedulable tasks found in planning payloads")
    return tuple(tasks)


def schedule_tasks(
    tasks: Iterable[SchedulableTask],
    drones: Iterable[DroneState],
    *,
    strategy: str,
) -> ScheduleResult:
    """Assign tasks to simulated drones with one deterministic strategy."""

    task_list = sorted(tuple(tasks), key=lambda task: task.task_id)
    drone_list = sorted((drone for drone in drones if drone.status == "idle"), key=lambda drone: drone.drone_id)
    if not drone_list:
        return ScheduleResult(
            strategy=strategy,
            assignments=(),
            unassigned_tasks=tuple(task.task_id for task in task_list),
            metrics=_empty_metrics(len(task_list)),
            notes=("no idle drones available",),
        )

    state = {
        drone.drone_id: {
            "available_at_min": drone.available_at_min,
            "active_time_min": 0.0,
            "distance_m": 0.0,
            "assignment_count": 0,
        }
        for drone in drone_list
    }
    assignments: list[Assignment] = []
    unassigned: list[str] = []
    for index, task in enumerate(task_list):
        drone = _select_drone(task, drone_list, state, strategy=strategy, round_robin_index=index)
        if drone is None:
            unassigned.append(task.task_id)
            continue
        estimate = _estimate_task_for_drone(task, drone)
        start = float(state[drone.drone_id]["available_at_min"])
        end = start + estimate["duration_min"]
        assignment = Assignment(
            task_id=task.task_id,
            drone_id=drone.drone_id,
            strategy=strategy,
            start_min=round(start, 3),
            end_min=round(end, 3),
            duration_min=round(estimate["duration_min"], 3),
            travel_distance_m=round(estimate["travel_distance_m"], 3),
            target_location_id=task.target_location_id,
            target_name=task.target_name,
            action=task.action,
        )
        assignments.append(assignment)
        state[drone.drone_id]["available_at_min"] = end
        state[drone.drone_id]["active_time_min"] += estimate["duration_min"]
        state[drone.drone_id]["distance_m"] += estimate["travel_distance_m"]
        state[drone.drone_id]["assignment_count"] += 1

    return ScheduleResult(
        strategy=strategy,
        assignments=tuple(assignments),
        unassigned_tasks=tuple(unassigned),
        metrics=_schedule_metrics(assignments, drone_list, state, total_tasks=len(task_list)),
        notes=(
            "Week 5 deterministic scheduling simulation; not safety validation, route optimization, or execution.",
        ),
    )


def compare_scheduling_strategies(
    tasks: Iterable[SchedulableTask],
    drones: Iterable[DroneState],
    *,
    strategies: Iterable[str] = ("round_robin", "least_loaded", "nearest_available"),
) -> dict[str, Any]:
    """Run multiple deterministic scheduling baselines over the same inputs."""

    task_tuple = tuple(tasks)
    drone_tuple = tuple(drones)
    results = [schedule_tasks(task_tuple, drone_tuple, strategy=strategy) for strategy in strategies]
    return {
        "strategy_results": [result.to_dict() for result in results],
        "comparison_table": [_comparison_row(result) for result in results],
        "best_strategy_by_makespan": _best_strategy(results, "makespan_min"),
        "notes": [
            "Classical deterministic baselines only; no LLM assignment is used.",
            "Metrics are synthetic scheduling proxies over the custom map, not physical flight performance.",
        ],
    }


def render_assignment_markdown(result: ScheduleResult) -> str:
    """Render one assignment table and metrics summary as Markdown."""

    lines = [
        f"# Week 5 Assignment Table - {result.strategy}",
        "",
        "This table is a simulated scheduling artifact. It is not route optimization, safety validation, or execution.",
        "",
        "| Task | Drone | Start min | End min | Duration min | Distance m | Target | Action |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for assignment in result.assignments:
        lines.append(
            "| "
            + " | ".join(
                [
                    assignment.task_id,
                    assignment.drone_id,
                    f"{assignment.start_min:.3f}",
                    f"{assignment.end_min:.3f}",
                    f"{assignment.duration_min:.3f}",
                    f"{assignment.travel_distance_m:.3f}",
                    assignment.target_name,
                    assignment.action,
                ]
            )
            + " |"
        )
    lines.extend(["", "## Metrics", ""])
    for key, value in result.metrics.items():
        lines.append(f"- `{key}`: `{value}`")
    if result.unassigned_tasks:
        lines.extend(["", "## Unassigned Tasks", ""])
        lines.extend(f"- `{task_id}`" for task_id in result.unassigned_tasks)
    return "\n".join(lines) + "\n"


def render_assignment_csv(result: ScheduleResult) -> str:
    """Render assignment rows as CSV text."""

    header = "task_id,drone_id,strategy,start_min,end_min,duration_min,travel_distance_m,target_location_id,target_name,action"
    rows = [header]
    for assignment in result.assignments:
        rows.append(
            ",".join(
                [
                    assignment.task_id,
                    assignment.drone_id,
                    assignment.strategy,
                    str(assignment.start_min),
                    str(assignment.end_min),
                    str(assignment.duration_min),
                    str(assignment.travel_distance_m),
                    assignment.target_location_id,
                    _csv_escape(assignment.target_name),
                    assignment.action,
                ]
            )
        )
    return "\n".join(rows) + "\n"


def render_allocation_html(result: ScheduleResult) -> str:
    """Render a lightweight HTML allocation timeline."""

    makespan = max((assignment.end_min for assignment in result.assignments), default=1.0)
    rows = []
    for assignment in result.assignments:
        left = (assignment.start_min / makespan) * 100 if makespan else 0.0
        width = max((assignment.duration_min / makespan) * 100 if makespan else 0.0, 1.0)
        rows.append(
            f"<tr><td>{assignment.drone_id}</td><td>{assignment.task_id}</td><td>{assignment.target_name}</td>"
            f"<td><div class='track'><div class='bar' style='margin-left:{left:.2f}%;width:{width:.2f}%'>{assignment.action}</div></div></td></tr>"
        )
    return (
        "<!doctype html>\n<html><head><meta charset='utf-8'><title>Week 5 Drone Allocation</title>"
        "<style>body{font-family:Arial,sans-serif;margin:24px;color:#202124}"
        "table{border-collapse:collapse;width:100%}td,th{border:1px solid #dadce0;padding:8px;text-align:left}"
        ".track{background:#eef1f4;height:28px;position:relative}.bar{background:#2f6f6d;color:white;height:28px;line-height:28px;padding-left:6px;box-sizing:border-box;white-space:nowrap;overflow:hidden}"
        "</style></head><body>"
        f"<h1>Week 5 Drone Allocation - {result.strategy}</h1>"
        "<p>Simulated assignment visualization only; not route optimization, safety validation, or execution.</p>"
        "<table><thead><tr><th>Drone</th><th>Task</th><th>Target</th><th>Timeline</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></body></html>\n"
    )


def _select_drone(
    task: SchedulableTask,
    drones: list[DroneState],
    state: dict[str, dict[str, float]],
    *,
    strategy: str,
    round_robin_index: int,
) -> DroneState | None:
    if not drones:
        return None
    if strategy == "round_robin":
        return drones[round_robin_index % len(drones)]
    if strategy == "least_loaded":
        return min(
            drones,
            key=lambda drone: (
                state[drone.drone_id]["available_at_min"] + _estimate_task_for_drone(task, drone)["duration_min"],
                state[drone.drone_id]["assignment_count"],
                drone.drone_id,
            ),
        )
    if strategy == "nearest_available":
        return min(
            drones,
            key=lambda drone: (
                state[drone.drone_id]["available_at_min"],
                _one_way_distance_m(drone, task),
                drone.drone_id,
            ),
        )
    raise ValueError(f"unsupported scheduling strategy: {strategy}")


def _estimate_task_for_drone(task: SchedulableTask, drone: DroneState) -> dict[str, float]:
    one_way = _one_way_distance_m(drone, task)
    round_trip = one_way * 2.0
    travel_time = round_trip / max(drone.speed_m_per_min, 1.0)
    return {
        "duration_min": task.estimated_work_min + travel_time,
        "travel_distance_m": round_trip,
    }


def _one_way_distance_m(drone: DroneState, task: SchedulableTask) -> float:
    return _haversine_m(
        drone.current_latitude,
        drone.current_longitude,
        task.target_latitude,
        task.target_longitude,
    )


def _estimate_work_minutes(plan: Mapping[str, Any]) -> float:
    step_actions = [str(step.get("action")) for step in plan.get("steps", []) if isinstance(step, Mapping)]
    durations = {
        "validate_grounding": 0.2,
        "review_constraints": 0.5,
        "takeoff": 1.0,
        "fly_to": 0.0,
        "scan_area": 4.0,
        "inspect_area": 3.0,
        "search_area": 5.0,
        "hold_position": 2.0,
        "position_at_location": 1.5,
        "return_to_grounded_location": 1.5,
        "capture_images": 2.0,
        "run_vision_model": 1.0,
        "save_observation_results": 0.5,
        "return_to_launch_area": 0.0,
        "hold_for_scheduler": 0.2,
        "land": 1.0,
    }
    return sum(durations.get(action, 1.0) for action in step_actions)


def _schedule_metrics(
    assignments: list[Assignment],
    drones: list[DroneState],
    state: dict[str, dict[str, float]],
    *,
    total_tasks: int,
) -> dict[str, Any]:
    active_times = [state[drone.drone_id]["active_time_min"] for drone in drones]
    assignment_counts = [state[drone.drone_id]["assignment_count"] for drone in drones]
    response_delays = [assignment.start_min for assignment in assignments]
    makespan = max((assignment.end_min for assignment in assignments), default=0.0)
    return {
        "total_tasks": total_tasks,
        "assigned_tasks": len(assignments),
        "unassigned_tasks": total_tasks - len(assignments),
        "drones_used": sum(1 for count in assignment_counts if count > 0),
        "makespan_min": round(makespan, 3),
        "total_active_time_min": round(sum(active_times), 3),
        "total_travel_distance_m": round(sum(state[drone.drone_id]["distance_m"] for drone in drones), 3),
        "workload_range_min": round((max(active_times) - min(active_times)) if active_times else 0.0, 3),
        "assignment_count_range": int(max(assignment_counts) - min(assignment_counts)) if assignment_counts else 0,
        "mean_response_delay_min": round(sum(response_delays) / len(response_delays), 3) if response_delays else 0.0,
    }


def _empty_metrics(total_tasks: int) -> dict[str, Any]:
    return {
        "total_tasks": total_tasks,
        "assigned_tasks": 0,
        "unassigned_tasks": total_tasks,
        "drones_used": 0,
        "makespan_min": 0.0,
        "total_active_time_min": 0.0,
        "total_travel_distance_m": 0.0,
        "workload_range_min": 0.0,
        "assignment_count_range": 0,
        "mean_response_delay_min": 0.0,
    }


def _comparison_row(result: ScheduleResult) -> dict[str, Any]:
    return {
        "strategy": result.strategy,
        "assigned_tasks": result.metrics["assigned_tasks"],
        "unassigned_tasks": result.metrics["unassigned_tasks"],
        "drones_used": result.metrics["drones_used"],
        "makespan_min": result.metrics["makespan_min"],
        "total_travel_distance_m": result.metrics["total_travel_distance_m"],
        "workload_range_min": result.metrics["workload_range_min"],
    }


def _best_strategy(results: list[ScheduleResult], metric: str) -> str | None:
    complete = [result for result in results if result.metrics.get("unassigned_tasks") == 0]
    if not complete:
        return None
    return min(complete, key=lambda result: (float(result.metrics[metric]), result.strategy)).strategy


def _positive_count(value: Any) -> int:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value > 0:
        return int(value)
    return 1


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return radius_m * c


def _csv_escape(value: str) -> str:
    if "," not in value and '"' not in value:
        return value
    return '"' + value.replace('"', '""') + '"'
