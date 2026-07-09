"""Deterministic Week 4 mission planning over grounded map objects.

The planner consumes Week 3 grounding output and emits inspectable task
sequences. It does not allocate drones, optimize routes, execute simulation,
or certify safety.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

import networkx as nx

from shepherd_ai.grounding import GroundedIntent, GroundedMapObject, grounded_map_objects


SUPPORTED_ACTIONS = {"capture", "hold", "inspect", "return", "scan", "search", "send"}
OBSERVATION_ACTIONS = {"capture", "inspect", "scan", "search"}


@dataclass(frozen=True)
class MissionPlanStep:
    """One validated high-level mission-planning step."""

    step_id: str
    action: str
    description: str
    depends_on: tuple[str, ...] = field(default_factory=tuple)
    map_object: dict[str, Any] | None = None
    expected_output: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["depends_on"] = list(self.depends_on)
        payload["notes"] = list(self.notes)
        return payload


@dataclass(frozen=True)
class MissionPlan:
    """Serializable mission plan produced from one grounded intent."""

    status: str
    ready_for_scheduling: bool
    intent: dict[str, Any]
    primary_map_object: dict[str, Any] | None
    referenced_map_objects: tuple[dict[str, Any], ...]
    steps: tuple[MissionPlanStep, ...]
    issues: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "ready_for_scheduling": self.ready_for_scheduling,
            "intent": self.intent,
            "primary_map_object": self.primary_map_object,
            "referenced_map_objects": list(self.referenced_map_objects),
            "steps": [step.to_dict() for step in self.steps],
            "task_graph": mission_plan_task_graph(self),
            "issues": list(self.issues),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class MissionPlanValidation:
    """Deterministic validation report for a mission plan contract."""

    valid: bool
    issues: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "issues": list(self.issues),
            "warnings": list(self.warnings),
        }


def plan_grounded_mission(grounded_intent: GroundedIntent | Mapping[str, Any]) -> MissionPlan:
    """Build a deterministic mission plan from grounded intent output."""

    grounded = _coerce_grounded_intent(grounded_intent)
    intent = dict(grounded.intent)
    issues = list(grounded.issues)
    notes = [
        "Week 4 deterministic mission plan; not scheduling, execution, or safety validation.",
    ]

    if not grounded.ready_for_planning:
        return _blocked_plan(
            grounded,
            "grounding_not_ready_for_planning",
            notes=notes,
        )

    action = intent.get("action")
    if action not in SUPPORTED_ACTIONS:
        return _blocked_plan(
            grounded,
            "unsupported_or_missing_action",
            notes=notes,
        )

    map_objects = grounded_map_objects(grounded)
    if not map_objects:
        return _blocked_plan(
            grounded,
            "no_grounded_map_object",
            notes=notes,
        )

    primary = _select_primary_map_object(map_objects)
    referenced_map_objects = tuple(map_object.to_dict() for map_object in map_objects)
    issues.extend(_planning_cautions(map_objects, primary))
    steps = _build_steps(intent, primary, referenced_map_objects=referenced_map_objects)
    return MissionPlan(
        status="planned",
        ready_for_scheduling=True,
        intent=intent,
        primary_map_object=primary.to_dict(),
        referenced_map_objects=referenced_map_objects,
        steps=tuple(steps),
        issues=tuple(dict.fromkeys(issues)),
        notes=tuple(notes),
    )


def validate_mission_plan(plan: MissionPlan) -> MissionPlanValidation:
    """Validate the task-sequence contract before scheduling consumes it."""

    issues: list[str] = []
    warnings: list[str] = []

    if plan.status not in {"planned", "blocked"}:
        issues.append("unsupported_plan_status")

    if plan.status == "blocked":
        if plan.ready_for_scheduling:
            issues.append("blocked_plan_marked_ready_for_scheduling")
        if plan.steps:
            issues.append("blocked_plan_must_not_have_steps")
        return MissionPlanValidation(valid=not issues, issues=tuple(issues), warnings=tuple(warnings))

    if not plan.ready_for_scheduling:
        issues.append("planned_plan_not_ready_for_scheduling")
    if not plan.primary_map_object:
        issues.append("planned_plan_missing_primary_map_object")
    elif not _primary_map_object_has_coordinates(plan.primary_map_object):
        issues.append("primary_map_object_missing_coordinates")
    if not plan.steps:
        issues.append("planned_plan_missing_steps")
        return MissionPlanValidation(valid=False, issues=tuple(dict.fromkeys(issues)), warnings=tuple(warnings))

    step_ids = [step.step_id for step in plan.steps]
    if len(step_ids) != len(set(step_ids)):
        issues.append("duplicate_step_ids")

    seen: set[str] = set()
    for index, step in enumerate(plan.steps):
        if not step.step_id:
            issues.append("empty_step_id")
        if not step.action:
            issues.append(f"{step.step_id}_missing_action")
        if not step.description:
            issues.append(f"{step.step_id}_missing_description")
        if not step.expected_output:
            issues.append(f"{step.step_id}_missing_expected_output")
        if index == 0 and step.depends_on:
            issues.append("first_step_must_not_have_dependencies")
        if index > 0 and not step.depends_on:
            issues.append(f"{step.step_id}_missing_dependency")
        for dependency in step.depends_on:
            if dependency == step.step_id:
                issues.append(f"{step.step_id}_depends_on_itself")
            if dependency not in seen:
                issues.append(f"{step.step_id}_has_unknown_or_forward_dependency_{dependency}")
        if step.action in _map_required_step_actions() and not _step_has_map_coordinates(step):
            issues.append(f"{step.step_id}_missing_map_coordinates")
        seen.add(step.step_id)

    action = str(plan.intent.get("action") or "")
    required_actions = _required_step_actions_for_intent(action, plan.intent.get("constraints", []))
    present_actions = {step.action for step in plan.steps}
    missing_actions = sorted(required_actions - present_actions)
    issues.extend(f"missing_required_step_action_{action_name}" for action_name in missing_actions)
    if "primary_map_object_not_flyable" in plan.issues:
        warnings.append("primary map object is not flyable; later safety validation must decide whether to reject it")
    if "primary_map_object_requires_clearance" in plan.issues:
        warnings.append("primary map object requires clearance; later safety validation must decide whether to reject it")

    return MissionPlanValidation(
        valid=not issues,
        issues=tuple(dict.fromkeys(issues)),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def mission_plan_task_graph(plan: MissionPlan) -> dict[str, Any]:
    """Return an explicit node/edge view of the plan dependencies."""

    graph = mission_plan_networkx_graph(plan)
    return {
        "nodes": [
            {
                "id": node_id,
                "action": node_payload["action"],
                "expected_output": node_payload["expected_output"],
            }
            for node_id, node_payload in graph.nodes(data=True)
        ],
        "edges": [
            {"from": source, "to": target}
            for source, target in graph.edges()
        ],
    }


def mission_plan_networkx_graph(plan: MissionPlan) -> nx.DiGraph:
    """Build a NetworkX dependency graph for the mission plan."""

    graph = nx.DiGraph()
    for step in plan.steps:
        graph.add_node(
            step.step_id,
            action=step.action,
            description=step.description,
            expected_output=step.expected_output,
        )
    for step in plan.steps:
        for dependency in step.depends_on:
            graph.add_edge(dependency, step.step_id)
    return graph


def mission_plan_mermaid(plan: MissionPlan) -> str:
    """Render a Mermaid flow diagram for documentation and notebook inspection."""

    lines = ["flowchart TD"]
    if not plan.steps:
        lines.append('    blocked["Blocked: planning not ready"]')
        for issue in plan.issues:
            lines.append(f'    issue_{_mermaid_id(issue)}["Issue: {_escape_mermaid(issue)}"]')
            lines.append(f"    blocked --> issue_{_mermaid_id(issue)}")
        return "\n".join(lines) + "\n"

    for step in plan.steps:
        label = f"{step.step_id}: {step.action}"
        lines.append(f'    {step.step_id}["{_escape_mermaid(label)}"]')
    for edge in mission_plan_task_graph(plan)["edges"]:
        lines.append(f"    {edge['from']} --> {edge['to']}")
    return "\n".join(lines) + "\n"


def _blocked_plan(
    grounded_intent: GroundedIntent,
    issue: str,
    *,
    notes: list[str],
) -> MissionPlan:
    return MissionPlan(
        status="blocked",
        ready_for_scheduling=False,
        intent=dict(grounded_intent.intent),
        primary_map_object=None,
        referenced_map_objects=(),
        steps=(),
        issues=tuple(dict.fromkeys((*grounded_intent.issues, issue))),
        notes=tuple(notes),
    )


def _build_steps(
    intent: dict[str, Any],
    primary: GroundedMapObject,
    *,
    referenced_map_objects: tuple[dict[str, Any], ...],
) -> list[MissionPlanStep]:
    action = str(intent.get("action") or "inspect")
    target_name = primary.name
    primary_payload = primary.to_dict()
    steps = [
        MissionPlanStep(
            step_id="step_001",
            action="validate_grounding",
            description=f"Confirm grounded map object {primary.location_id} is available to the planner.",
            map_object=primary_payload,
            expected_output="validated_grounded_map_object",
        ),
    ]

    current_step_id = "step_001"
    constraints = intent.get("constraints", [])
    if isinstance(constraints, list) and constraints:
        review_step_id = _next_step_id(len(steps) + 1)
        steps.append(
            MissionPlanStep(
                step_id=review_step_id,
                action="review_constraints",
                description="Review command constraints before creating schedulable flight tasks.",
                depends_on=(current_step_id,),
                expected_output="constraints_available_for_later_safety_validation",
                notes=tuple(str(constraint) for constraint in constraints),
            )
        )
        current_step_id = review_step_id

    takeoff_step_id = _next_step_id(len(steps) + 1)
    steps.append(
        MissionPlanStep(
            step_id=takeoff_step_id,
            action="takeoff",
            description="Prepare a simulated drone takeoff task for later scheduling.",
            depends_on=(current_step_id,),
            expected_output="airborne_simulated_drone",
        )
    )

    fly_step_id = _next_step_id(len(steps) + 1)
    steps.append(
        MissionPlanStep(
            step_id=fly_step_id,
            action="fly_to",
            description=f"Navigate to {target_name} using the grounded center coordinates.",
            depends_on=(takeoff_step_id,),
            map_object=primary_payload,
            expected_output="drone_at_grounded_location",
        )
    )

    mission_step = _mission_action_step(action, primary, depends_on=fly_step_id, step_id=_next_step_id(len(steps) + 1))
    steps.append(mission_step)
    if action in OBSERVATION_ACTIONS:
        if action != "capture":
            capture_step_id = _next_step_id(len(steps) + 1)
            steps.append(
                MissionPlanStep(
                    step_id=capture_step_id,
                    action="capture_images",
                    description=f"Capture simulated imagery at {target_name} for later vision processing.",
                    depends_on=(mission_step.step_id,),
                    map_object=primary_payload,
                    expected_output="captured_image_batch_reference",
                )
            )
            previous_step_id = capture_step_id
        else:
            previous_step_id = mission_step.step_id
        vision_step_id = _next_step_id(len(steps) + 1)
        steps.append(
            MissionPlanStep(
                step_id=vision_step_id,
                action="run_vision_model",
                description="Create a planned downstream vision-inference task for the captured imagery.",
                depends_on=(previous_step_id,),
                map_object=primary_payload,
                expected_output="vision_inference_task_record",
                notes=("Week 4 plans this task; Week 6 implements actual YOLO inference.",),
            )
        )
        save_step_id = _next_step_id(len(steps) + 1)
        steps.append(
            MissionPlanStep(
                step_id=save_step_id,
                action="save_observation_results",
                description="Store simulated observation outputs for later reporting and evaluation.",
                depends_on=(vision_step_id,),
                map_object=primary_payload,
                expected_output="saved_observation_record",
            )
        )
        return_step_id = _next_step_id(len(steps) + 1)
        steps.append(
            MissionPlanStep(
                step_id=return_step_id,
                action="return_to_launch_area",
                description="Return the simulated drone to the launch area after the observation task.",
                depends_on=(save_step_id,),
                expected_output="return_task_for_scheduler",
            )
        )
    elif action == "return":
        land_step_id = _next_step_id(len(steps) + 1)
        steps.append(
            MissionPlanStep(
                step_id=land_step_id,
                action="land",
                description=f"Land at {target_name} after return navigation.",
                depends_on=(mission_step.step_id,),
                map_object=primary_payload,
                expected_output="landed_simulated_drone",
            )
        )
    else:
        hold_step_id = _next_step_id(len(steps) + 1)
        steps.append(
            MissionPlanStep(
                step_id=hold_step_id,
                action="hold_for_scheduler",
                description="Hold this grounded task for later multi-drone scheduling.",
                depends_on=(mission_step.step_id,),
                map_object=primary_payload,
                expected_output="schedulable_grounded_task",
            )
        )
    return steps


def _mission_action_step(
    action: str,
    primary: GroundedMapObject,
    *,
    depends_on: str,
    step_id: str,
) -> MissionPlanStep:
    action_by_intent = {
        "capture": "capture_images",
        "hold": "hold_position",
        "inspect": "inspect_area",
        "return": "return_to_grounded_location",
        "scan": "scan_area",
        "search": "search_area",
        "send": "position_at_location",
    }
    planned_action = action_by_intent[action]
    return MissionPlanStep(
        step_id=step_id,
        action=planned_action,
        description=_mission_description(action, primary),
        depends_on=(depends_on,),
        map_object=primary.to_dict(),
        expected_output=f"{planned_action}_complete",
    )


def _mission_description(action: str, primary: GroundedMapObject) -> str:
    descriptions = {
        "capture": f"Capture simulated imagery at {primary.name}.",
        "hold": f"Hold simulated position over {primary.name}.",
        "inspect": f"Inspect {primary.name} and collect simulated observations.",
        "return": f"Return simulated drone resources to {primary.name}.",
        "scan": f"Scan {primary.name} and collect simulated observations.",
        "search": f"Search {primary.name} and collect simulated observations.",
        "send": f"Position simulated drone resources at {primary.name}.",
    }
    return descriptions[action]


def _select_primary_map_object(map_objects: list[GroundedMapObject]) -> GroundedMapObject:
    priority = {"target": 0, "location": 1}
    return sorted(
        map_objects,
        key=lambda item: (priority.get(item.reference_field, 2), item.reference_field, item.location_id),
    )[0]


def _planning_cautions(map_objects: list[GroundedMapObject], primary: GroundedMapObject) -> list[str]:
    cautions: list[str] = []
    if not primary.flyable:
        cautions.append("primary_map_object_not_flyable")
    if primary.requires_clearance:
        cautions.append("primary_map_object_requires_clearance")
    for map_object in map_objects:
        if map_object.location_id == primary.location_id and map_object.reference_field == primary.reference_field:
            continue
        if not map_object.flyable:
            cautions.append(f"{map_object.reference_field}_referenced_map_object_not_flyable")
        if map_object.requires_clearance:
            cautions.append(f"{map_object.reference_field}_referenced_map_object_requires_clearance")
    return cautions


def _required_step_actions_for_intent(action: str, constraints: Any = None) -> set[str]:
    required = {"validate_grounding", "takeoff", "fly_to"}
    if isinstance(constraints, list) and constraints:
        required.add("review_constraints")
    mission_action = {
        "capture": "capture_images",
        "hold": "hold_position",
        "inspect": "inspect_area",
        "return": "return_to_grounded_location",
        "scan": "scan_area",
        "search": "search_area",
        "send": "position_at_location",
    }.get(action)
    if mission_action:
        required.add(mission_action)
    if action in OBSERVATION_ACTIONS:
        required.update({"capture_images", "run_vision_model", "save_observation_results", "return_to_launch_area"})
    elif action == "return":
        required.add("land")
    elif action in {"hold", "send"}:
        required.add("hold_for_scheduler")
    return required


def _next_step_id(index: int) -> str:
    return f"step_{index:03d}"


def _map_required_step_actions() -> set[str]:
    return {
        "capture_images",
        "fly_to",
        "hold_for_scheduler",
        "hold_position",
        "inspect_area",
        "land",
        "position_at_location",
        "return_to_grounded_location",
        "run_vision_model",
        "save_observation_results",
        "scan_area",
        "search_area",
        "validate_grounding",
    }


def _primary_map_object_has_coordinates(map_object: dict[str, Any]) -> bool:
    center = map_object.get("center")
    return (
        isinstance(map_object.get("location_id"), str)
        and isinstance(center, dict)
        and isinstance(center.get("latitude"), (int, float))
        and isinstance(center.get("longitude"), (int, float))
    )


def _step_has_map_coordinates(step: MissionPlanStep) -> bool:
    return isinstance(step.map_object, dict) and _primary_map_object_has_coordinates(step.map_object)


def _coerce_grounded_intent(payload: GroundedIntent | Mapping[str, Any]) -> GroundedIntent:
    if isinstance(payload, GroundedIntent):
        return payload
    if not isinstance(payload, Mapping):
        raise TypeError("grounded_intent must be a GroundedIntent or mapping")
    raise TypeError("planning from serialized mappings is not implemented; pass a GroundedIntent object")


def _escape_mermaid(value: str) -> str:
    return value.replace('"', "'")


def _mermaid_id(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value)[:64]
