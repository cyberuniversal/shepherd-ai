"""Bounded interactive interface for the Week 8 mission simulator."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from shepherd_ai.grounding import MapLocation
from shepherd_ai.mission_simulation import schedule_from_payload, simulate_schedule
from shepherd_ai.safety import SafetyPolicy
from shepherd_ai.scheduling import load_drones
from shepherd_ai.week8_pipeline import prepare_week8_mission


DEFAULT_COMMAND = (
    "Send two drones north to inspect crops and one drone east to inspect irrigation."
)


class InteractiveMissionDemo:
    """Run typed commands through the validated Python simulation pipeline."""

    def __init__(
        self,
        locations: Iterable[MapLocation],
        fleet_payload: Mapping[str, Any],
        safety_policy: SafetyPolicy,
    ) -> None:
        self._locations = tuple(locations)
        self._location_index = {location.id: location for location in self._locations}
        self._fleet_payload = dict(fleet_payload)
        self._safety_policy = safety_policy
        self._drones = load_drones(self._fleet_payload, self._location_index)

    def config(self) -> dict[str, Any]:
        return {
            "default_command": DEFAULT_COMMAND,
            "map_locations": [location.to_dict() for location in self._locations],
            "drones": [drone.to_dict() for drone in self._drones],
            "safety_policy": self._safety_policy.to_dict(),
            "research_status": "week8_in_progress",
            "limitations": [
                "Typed-command interface only; exact-scenario ASR evidence is still missing.",
                "Mission-assigned imagery and mission vision results are still missing.",
                "The 3D renderer visualizes deterministic telemetry and is not a flight-physics engine.",
            ],
        }

    def run(
        self,
        command: str,
        *,
        grounding_resolutions: Mapping[str, str] | None = None,
        time_step_min: float = 0.25,
    ) -> dict[str, Any]:
        text = command.strip()
        if not text:
            raise ValueError("command must not be empty")
        preparation = prepare_week8_mission(
            text,
            locations=self._locations,
            fleet_payload=self._fleet_payload,
            safety_policy=self._safety_policy,
            grounding_resolutions=grounding_resolutions,
        )
        if preparation["status"] == "clarification_required":
            return {
                "status": "clarification_required",
                "command": text,
                "clarifications": _clarifications(preparation),
                "preparation": preparation,
                "simulation": None,
                "research_status": "blocked_before_simulation",
            }
        if preparation.get("schedule") is None:
            return {
                "status": "pipeline_blocked",
                "command": text,
                "clarifications": [],
                "preparation": preparation,
                "simulation": None,
                "research_status": "blocked_before_simulation",
            }
        safety = preparation.get("safety_report") or {}
        if safety.get("status") != "approved":
            return {
                "status": "safety_blocked",
                "command": text,
                "clarifications": [],
                "preparation": preparation,
                "simulation": None,
                "research_status": "blocked_before_simulation",
            }
        simulation = simulate_schedule(
            schedule_from_payload(preparation["schedule"]),
            self._drones,
            self._locations,
            self._safety_policy,
            time_step_min=time_step_min,
            task_behaviors=_task_behaviors(preparation),
        )
        return {
            "status": "simulation_ready",
            "command": text,
            "clarifications": [],
            "preparation": preparation,
            "simulation": simulation,
            "research_status": "missing_required_week8_evidence",
        }


def _clarifications(preparation: Mapping[str, Any]) -> list[dict[str, Any]]:
    blocking = set(str(value) for value in preparation.get("blocking_clauses", []))
    requests: list[dict[str, Any]] = []
    for clause in preparation.get("clause_results", []):
        clause_id = str(clause.get("clause_id", ""))
        if clause_id not in blocking:
            continue
        seen: set[str] = set()
        options: list[dict[str, Any]] = []
        grounded = clause.get("grounded_intent", {})
        for reference in grounded.get("references", []):
            location = reference.get("location")
            if not isinstance(location, Mapping):
                continue
            location_id = str(location.get("id", ""))
            if not location_id or location_id in seen:
                continue
            seen.add(location_id)
            options.append(
                {
                    "location_id": location_id,
                    "name": str(location.get("name", location_id)),
                    "reference_field": str(reference.get("field", "")),
                    "phrase": reference.get("phrase"),
                    "category": str(location.get("category", "")),
                }
            )
        requests.append(
            {
                "clause_id": clause_id,
                "text": str(clause.get("text", "")),
                "message": "Choose the intended destination before planning continues.",
                "issues": list(clause.get("issues", [])),
                "options": sorted(options, key=lambda option: option["location_id"]),
            }
        )
    if not requests:
        requests.append(
            {
                "clause_id": None,
                "text": str(preparation.get("decomposition", {}).get("source_text", "")),
                "message": "The command needs clarification before planning can continue.",
                "issues": list(preparation.get("issues", [])),
                "options": [],
            }
        )
    return requests


def _task_behaviors(preparation: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    perception_by_plan: dict[str, Mapping[str, Any]] = {}
    for target in preparation.get("perception_targets", []):
        clause_id = str(target.get("clause_id", ""))
        if clause_id.startswith("clause_"):
            perception_by_plan[f"mission_{clause_id.removeprefix('clause_')}"] = target
    behaviors: dict[str, dict[str, Any]] = {}
    schedule = preparation.get("schedule") or {}
    for assignment in schedule.get("assignments", []):
        task_id = str(assignment.get("task_id", ""))
        plan_id = "_".join(task_id.split("_")[:2])
        target = perception_by_plan.get(plan_id)
        if target is None:
            continue
        behaviors[task_id] = {
            "mode": "search",
            "perception_target": target.get("phrase"),
            "observation_status": "awaiting_mission_imagery",
            "known_target_coordinates": False,
        }
    return behaviors
