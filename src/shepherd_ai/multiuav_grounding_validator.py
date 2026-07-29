"""Deterministic recursive grounding for MultiUAV API plans."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import re
from typing import Any, Mapping

from shepherd_ai.multiuav_context import validate_agent_visible_context
from shepherd_ai.multiuav_plan_contract import StrictModelOutput


ENDPOINT_SCHEMA_STAGE = "post_plan_endpoint_schema"
IDENTIFIER_STAGE = "post_plan_identifier_grounding"
PARAMETER_STAGE = "post_plan_parameter_grounding"
SAFETY_BOUNDS_STAGE = "post_plan_safety_bounds"
ACCEPTED_STAGE = "accepted"


@dataclass(frozen=True)
class EndpointSpec:
    required: frozenset[str]
    optional: frozenset[str] = frozenset()


ENDPOINT_SPECS = {
    "/drones/{id}/command/take_off": EndpointSpec(
        required=frozenset({"id", "altitude"})
    ),
    "/drones/{id}/command/land": EndpointSpec(required=frozenset({"id"})),
    "/drones/{id}/command/move_to": EndpointSpec(
        required=frozenset({"id", "x", "y"}),
        optional=frozenset({"z"}),
    ),
    "/drones/{id}/command/move_towards": EndpointSpec(
        required=frozenset({"id", "distance", "heading"})
    ),
    "/drones/{id}/command/move_along_path": EndpointSpec(
        required=frozenset({"id", "waypoints"})
    ),
    "/drones/{id}/command/change_altitude": EndpointSpec(
        required=frozenset({"id", "altitude"})
    ),
    "/drones/{id}/command/hover": EndpointSpec(
        required=frozenset({"id"}),
        optional=frozenset({"duration"}),
    ),
    "/drones/{id}/command/rotate": EndpointSpec(
        required=frozenset({"id", "heading"})
    ),
    "/drones/{id}/command/return_home": EndpointSpec(
        required=frozenset({"id"})
    ),
    "/drones/{id}/command/take_photo": EndpointSpec(
        required=frozenset({"id"})
    ),
    "/drones/{id}/command/broadcast": EndpointSpec(
        required=frozenset({"id", "message"})
    ),
}

_NUMERIC_PARAMETERS = frozenset(
    {"altitude", "x", "y", "z", "distance", "heading", "duration"}
)
_COMPASS_HEADINGS = {
    "north": 0.0,
    "northeast": 45.0,
    "east": 90.0,
    "southeast": 135.0,
    "south": 180.0,
    "southwest": 225.0,
    "west": 270.0,
    "northwest": 315.0,
}


@dataclass(frozen=True)
class ValidationIssue:
    stage: str
    code: str
    path: str
    message: str
    value: Any

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationEvidence:
    path: str
    parameter: str
    value: Any
    source_path: str
    basis: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanValidationReport:
    valid: bool
    containment_stage: str
    issues: tuple[ValidationIssue, ...]
    evidence: tuple[ValidationEvidence, ...]
    validated_call_count: int
    validated_parameter_leaf_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "containment_stage": self.containment_stage,
            "issues": [issue.to_dict() for issue in self.issues],
            "evidence": [item.to_dict() for item in self.evidence],
            "validated_call_count": self.validated_call_count,
            "validated_parameter_leaf_count": self.validated_parameter_leaf_count,
        }


def validate_grounded_plan(
    output: StrictModelOutput,
    context: Mapping[str, Any],
) -> PlanValidationReport:
    """Validate one parsed output using only AGENT-visible evidence."""

    validate_agent_visible_context(context)
    if output.decision != "EXECUTE":
        return PlanValidationReport(
            valid=True,
            containment_stage=ACCEPTED_STAGE,
            issues=(),
            evidence=(),
            validated_call_count=0,
            validated_parameter_leaf_count=0,
        )

    schema_issues = _validate_endpoint_schemas(output)
    if schema_issues:
        return _failure(ENDPOINT_SCHEMA_STAGE, schema_issues)

    drones = {
        str(drone["id"]): drone
        for drone in context["drones"]
        if isinstance(drone, Mapping) and "id" in drone
    }
    identifier_issues = _validate_identifiers(output, drones)
    if identifier_issues:
        return _failure(IDENTIFIER_STAGE, identifier_issues)

    evidence = _EvidenceIndex.from_context(context)
    evidence_records = _identifier_evidence(output, context)
    parameter_issues: list[ValidationIssue] = []
    leaf_count = 0
    for call_index, call in enumerate(output.api_plan):
        for name, value in call.parameters.items():
            path = f"api_plan[{call_index}].parameters.{name}"
            leaves = _parameter_leaves(name, value, path)
            leaf_count += len(leaves)
            for semantic_name, leaf_path, leaf in leaves:
                if semantic_name == "id":
                    continue
                issue, match = _validate_grounding(
                    semantic_name,
                    leaf,
                    leaf_path,
                    evidence,
                )
                if issue is not None:
                    parameter_issues.append(issue)
                if match is not None:
                    evidence_records.append(match)
    if parameter_issues:
        return _failure(
            PARAMETER_STAGE,
            parameter_issues,
            evidence=tuple(evidence_records),
            leaf_count=leaf_count,
        )

    bounds_issues = _validate_bounds(output, context, drones)
    if bounds_issues:
        return _failure(
            SAFETY_BOUNDS_STAGE,
            bounds_issues,
            evidence=tuple(evidence_records),
            leaf_count=leaf_count,
        )
    return PlanValidationReport(
        valid=True,
        containment_stage=ACCEPTED_STAGE,
        issues=(),
        evidence=tuple(evidence_records),
        validated_call_count=len(output.api_plan),
        validated_parameter_leaf_count=leaf_count,
    )


@dataclass(frozen=True)
class _NumericEvidence:
    value: float
    source_path: str
    basis: str


@dataclass(frozen=True)
class _EvidenceIndex:
    instruction: str
    normalized_instruction: str
    instruction_numbers: tuple[_NumericEvidence, ...]
    context_numbers: Mapping[str, tuple[_NumericEvidence, ...]]
    compass_headings: tuple[_NumericEvidence, ...]

    @classmethod
    def from_context(cls, context: Mapping[str, Any]) -> "_EvidenceIndex":
        instruction = str(context["instruction"])
        instruction_numbers = tuple(_instruction_numbers(instruction))
        context_numbers = _parameter_specific_context_numbers(context)
        normalized = _normalize_text(instruction)
        headings = tuple(
            _NumericEvidence(
                value=value,
                source_path=f"instruction.direction.{direction}",
                basis="registered_compass_heading",
            )
            for direction, value in _COMPASS_HEADINGS.items()
            if re.search(rf"\b{direction}\b", normalized)
        )
        return cls(
            instruction=instruction,
            normalized_instruction=normalized,
            instruction_numbers=instruction_numbers,
            context_numbers=context_numbers,
            compass_headings=headings,
        )

    def numeric_match(
        self,
        parameter_name: str,
        value: float,
    ) -> _NumericEvidence | None:
        candidates = list(self.instruction_numbers)
        if parameter_name == "heading":
            candidates.extend(self.compass_headings)
        candidates.extend(self.context_numbers.get(parameter_name, ()))
        return next(
            (
                item
                for item in candidates
                if math.isclose(item.value, value, rel_tol=0.0, abs_tol=1e-9)
            ),
            None,
        )


def _validate_endpoint_schemas(
    output: StrictModelOutput,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for index, call in enumerate(output.api_plan):
        path = f"api_plan[{index}]"
        spec = ENDPOINT_SPECS.get(call.endpoint)
        if spec is None:
            issues.append(
                _issue(
                    ENDPOINT_SCHEMA_STAGE,
                    "endpoint_not_allowed",
                    f"{path}.endpoint",
                    "endpoint is not in the frozen benchmark command catalog",
                    call.endpoint,
                )
            )
            continue
        actual = set(call.parameters)
        missing = spec.required - actual
        unknown = actual - spec.required - spec.optional
        if missing:
            issues.append(
                _issue(
                    ENDPOINT_SCHEMA_STAGE,
                    "missing_parameters",
                    f"{path}.parameters",
                    f"missing required parameters: {sorted(missing)}",
                    sorted(actual),
                )
            )
        if unknown:
            issues.append(
                _issue(
                    ENDPOINT_SCHEMA_STAGE,
                    "unknown_parameters",
                    f"{path}.parameters",
                    f"parameters outside endpoint schema: {sorted(unknown)}",
                    sorted(actual),
                )
            )
        issues.extend(_validate_parameter_shapes(call.parameters, path))
    return issues


def _validate_parameter_shapes(
    parameters: Mapping[str, Any],
    call_path: str,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for name, value in parameters.items():
        path = f"{call_path}.parameters.{name}"
        if name == "id" and not isinstance(value, str):
            issues.append(_type_issue(path, "id must be text", value))
        elif name in _NUMERIC_PARAMETERS and not _is_number(value):
            issues.append(_type_issue(path, f"{name} must be numeric", value))
        elif name == "message" and not isinstance(value, str):
            issues.append(_type_issue(path, "message must be text", value))
        elif name == "waypoints":
            issues.extend(_validate_waypoint_shape(value, path))
    return issues


def _validate_waypoint_shape(value: Any, path: str) -> list[ValidationIssue]:
    if not isinstance(value, list) or not value:
        return [_type_issue(path, "waypoints must be a non-empty array", value)]
    issues: list[ValidationIssue] = []
    for index, waypoint in enumerate(value):
        item_path = f"{path}[{index}]"
        if not isinstance(waypoint, Mapping):
            issues.append(_type_issue(item_path, "waypoint must be an object", waypoint))
            continue
        if not {"x", "y"}.issubset(waypoint) or not set(waypoint) <= {"x", "y", "z"}:
            issues.append(
                _issue(
                    ENDPOINT_SCHEMA_STAGE,
                    "waypoint_schema_mismatch",
                    item_path,
                    "waypoint requires x/y and permits optional z only",
                    dict(waypoint),
                )
            )
            continue
        for coordinate, coordinate_value in waypoint.items():
            if not _is_number(coordinate_value):
                issues.append(
                    _type_issue(
                        f"{item_path}.{coordinate}",
                        "waypoint coordinate must be numeric",
                        coordinate_value,
                    )
                )
    return issues


def _validate_identifiers(
    output: StrictModelOutput,
    drones: Mapping[str, Mapping[str, Any]],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for index, call in enumerate(output.api_plan):
        drone_id = call.parameters.get("id")
        if isinstance(drone_id, str) and drone_id not in drones:
            issues.append(
                _issue(
                    IDENTIFIER_STAGE,
                    "unknown_drone_id",
                    f"api_plan[{index}].parameters.id",
                    "drone id is absent from AGENT-visible context",
                    drone_id,
                )
            )
    return issues


def _parameter_leaves(
    name: str,
    value: Any,
    path: str,
) -> list[tuple[str, str, Any]]:
    if name != "waypoints":
        return [(name, path, value)]
    leaves: list[tuple[str, str, Any]] = []
    for index, waypoint in enumerate(value):
        for coordinate, coordinate_value in waypoint.items():
            leaves.append(
                (
                    coordinate,
                    f"{path}[{index}].{coordinate}",
                    coordinate_value,
                )
            )
    return leaves


def _validate_grounding(
    parameter_name: str,
    value: Any,
    path: str,
    evidence: _EvidenceIndex,
) -> tuple[ValidationIssue | None, ValidationEvidence | None]:
    if parameter_name == "message":
        normalized = _normalize_text(value)
        if normalized and normalized in evidence.normalized_instruction:
            return None, ValidationEvidence(
                path=path,
                parameter=parameter_name,
                value=value,
                source_path="instruction",
                basis="normalized_substring",
            )
        return (
            _issue(
                PARAMETER_STAGE,
                "ungrounded_message",
                path,
                "message is not supported by the visible instruction",
                value,
            ),
            None,
        )
    if _is_number(value):
        numeric = float(value)
        match = evidence.numeric_match(parameter_name, numeric)
        if match is not None:
            return None, ValidationEvidence(
                path=path,
                parameter=parameter_name,
                value=value,
                source_path=match.source_path,
                basis=match.basis,
            )
        return (
            _issue(
                PARAMETER_STAGE,
                "ungrounded_numeric_value",
                path,
                "numeric value lacks parameter-compatible visible evidence",
                value,
            ),
            None,
        )
    return (
        _issue(
            PARAMETER_STAGE,
            "ungrounded_parameter_value",
            path,
            "value is absent from the visible instruction/context",
            value,
        ),
        None,
    )


def _validate_bounds(
    output: StrictModelOutput,
    context: Mapping[str, Any],
    drones: Mapping[str, Mapping[str, Any]],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    width = _number_or_none(context["session"].get("canvas_width"))
    height = _number_or_none(context["session"].get("canvas_height"))
    for call_index, call in enumerate(output.api_plan):
        parameters = call.parameters
        drone = drones[str(parameters["id"])]
        max_altitude = _number_or_none(drone.get("max_altitude"))
        for name, value in parameters.items():
            path = f"api_plan[{call_index}].parameters.{name}"
            if name == "waypoints":
                for waypoint_index, waypoint in enumerate(value):
                    for coordinate, coordinate_value in waypoint.items():
                        issues.extend(
                            _coordinate_bound_issues(
                                coordinate,
                                float(coordinate_value),
                                f"{path}[{waypoint_index}].{coordinate}",
                                width,
                                height,
                                max_altitude,
                            )
                        )
            elif name in {"x", "y", "z"}:
                issues.extend(
                    _coordinate_bound_issues(
                        name,
                        float(value),
                        path,
                        width,
                        height,
                        max_altitude,
                    )
                )
            elif name == "altitude":
                if float(value) < 0 or (
                    max_altitude is not None and float(value) > max_altitude
                ):
                    issues.append(
                        _bounds_issue(path, "altitude exceeds visible drone limits", value)
                    )
            elif name == "heading" and not 0 <= float(value) < 360:
                issues.append(
                    _bounds_issue(path, "heading must be in [0, 360)", value)
                )
            elif name in {"distance", "duration"} and float(value) <= 0:
                issues.append(
                    _bounds_issue(path, f"{name} must be positive", value)
                )
    return issues


def _coordinate_bound_issues(
    coordinate: str,
    value: float,
    path: str,
    width: float | None,
    height: float | None,
    max_altitude: float | None,
) -> list[ValidationIssue]:
    limit = {"x": width, "y": height, "z": max_altitude}[coordinate]
    if value < 0 or (limit is not None and value > limit):
        return [_bounds_issue(path, f"{coordinate} is outside visible limits", value)]
    return []


def _instruction_numbers(instruction: str) -> list[_NumericEvidence]:
    evidence: list[_NumericEvidence] = []
    pattern = re.compile(r"(?<![A-Za-z0-9])[-+]?\d+(?:\.\d+)?")
    for match in pattern.finditer(instruction):
        prefix = instruction[max(0, match.start() - 16) : match.start()]
        if re.search(r"\b(?:drone|uav)\s*[-#]?\s*$", prefix, flags=re.IGNORECASE):
            continue
        evidence.append(
            _NumericEvidence(
                value=float(match.group()),
                source_path=f"instruction[{match.start()}:{match.end()}]",
                basis="explicit_instruction_number",
            )
        )
    return evidence


def _parameter_specific_context_numbers(
    context: Mapping[str, Any],
) -> dict[str, tuple[_NumericEvidence, ...]]:
    grouped: dict[str, list[_NumericEvidence]] = {
        "x": [],
        "y": [],
        "z": [],
        "altitude": [],
        "heading": [],
    }
    for index, drone in enumerate(context["drones"]):
        if not isinstance(drone, Mapping):
            continue
        for container_name in ("position", "home_position"):
            container = drone.get(container_name)
            if not isinstance(container, Mapping):
                continue
            for coordinate in ("x", "y", "z"):
                value = container.get(coordinate)
                if not _is_number(value):
                    continue
                item = _NumericEvidence(
                    value=float(value),
                    source_path=f"drones[{index}].{container_name}.{coordinate}",
                    basis="visible_drone_state",
                )
                grouped[coordinate].append(item)
                if coordinate == "z":
                    grouped["altitude"].append(item)
        heading = drone.get("heading")
        if _is_number(heading):
            grouped["heading"].append(
                _NumericEvidence(
                    value=float(heading),
                    source_path=f"drones[{index}].heading",
                    basis="visible_drone_state",
                )
            )
    return {name: tuple(items) for name, items in grouped.items()}


def _identifier_evidence(
    output: StrictModelOutput,
    context: Mapping[str, Any],
) -> list[ValidationEvidence]:
    indexes = {
        str(drone["id"]): index
        for index, drone in enumerate(context["drones"])
        if isinstance(drone, Mapping) and "id" in drone
    }
    return [
        ValidationEvidence(
            path=f"api_plan[{call_index}].parameters.id",
            parameter="id",
            value=call.parameters["id"],
            source_path=f"drones[{indexes[str(call.parameters['id'])]}].id",
            basis="exact_visible_identifier",
        )
        for call_index, call in enumerate(output.api_plan)
    ]


def _failure(
    stage: str,
    issues: list[ValidationIssue],
    *,
    evidence: tuple[ValidationEvidence, ...] = (),
    leaf_count: int = 0,
) -> PlanValidationReport:
    return PlanValidationReport(
        valid=False,
        containment_stage=stage,
        issues=tuple(issues),
        evidence=evidence,
        validated_call_count=0,
        validated_parameter_leaf_count=leaf_count,
    )


def _issue(
    stage: str,
    code: str,
    path: str,
    message: str,
    value: Any,
) -> ValidationIssue:
    return ValidationIssue(
        stage=stage,
        code=code,
        path=path,
        message=message,
        value=value,
    )


def _type_issue(path: str, message: str, value: Any) -> ValidationIssue:
    return _issue(
        ENDPOINT_SCHEMA_STAGE,
        "parameter_type_mismatch",
        path,
        message,
        value,
    )


def _bounds_issue(path: str, message: str, value: Any) -> ValidationIssue:
    return _issue(
        SAFETY_BOUNDS_STAGE,
        "value_out_of_bounds",
        path,
        message,
        value,
    )


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _number_or_none(value: Any) -> float | None:
    return float(value) if _is_number(value) else None


def _normalize_text(value: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value).lower()))
