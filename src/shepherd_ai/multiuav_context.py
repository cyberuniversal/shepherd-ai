"""Agent-visible context projection for the pinned MultiUAV-Plat benchmark."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


CONTEXT_SCHEMA_VERSION = 1
SESSION_FIELDS = (
    "id",
    "task_type",
    "canvas_width",
    "canvas_height",
    "is_distance_3d",
    "status",
)
DRONE_FIELDS = (
    "id",
    "name",
    "model",
    "status",
    "position",
    "heading",
    "speed",
    "perceived_radius",
    "task_radius",
    "battery_level",
    "battery_volume",
    "battery_capacity",
    "max_speed",
    "max_altitude",
    "home_position",
)
ENVIRONMENT_FIELDS = (
    "id",
    "name",
    "weather",
    "temperature",
    "humidity",
    "pressure",
    "wind_speed",
    "wind_direction",
    "visibility",
)
PRIVILEGED_SOURCE_FIELDS = frozenset(
    {
        "related_apis",
        "execution_check_apis",
        "commands",
        "history",
        "statistics",
        "content_aliases",
        "is_done",
        "is_passed",
        "targets",
        "obstacles",
    }
)
AGENT_OBSERVATION_ENDPOINTS = (
    "GET /drones",
    "GET /drones/{id}",
    "GET /drones/{id}/nearby",
    "GET /drones/{id}/nearby/drones",
    "GET /drones/{id}/nearby/targets",
    "GET /drones/{id}/nearby/obstacles",
    "GET /environments/current",
)


def project_agent_visible_context(
    session: Mapping[str, Any],
    *,
    task_id: str,
    instruction: str,
) -> dict[str, Any]:
    """Project only evidence available before planning to the AGENT role."""

    normalized_task_id = _nonempty_text(task_id, "task_id")
    normalized_instruction = _nonempty_text(instruction, "instruction")
    drones = session.get("drones")
    if not isinstance(drones, list) or not drones:
        raise ValueError("session drones must be a non-empty list")
    environment = session.get("environment")
    if not isinstance(environment, Mapping):
        raise ValueError("session environment must be an object")

    context = {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "role": "AGENT",
        "task_id": normalized_task_id,
        "instruction": normalized_instruction,
        "session": _project_fields(session, SESSION_FIELDS),
        "drones": [
            _project_fields(_require_mapping(drone, "drone"), DRONE_FIELDS)
            for drone in drones
        ],
        "environment": _project_fields(environment, ENVIRONMENT_FIELDS),
        "observation_contract": {
            "global_targets_visible": False,
            "global_obstacles_visible": False,
            "local_perception_required": True,
            "allowed_endpoints": list(AGENT_OBSERVATION_ENDPOINTS),
        },
    }
    validate_agent_visible_context(context)
    return context


def validate_agent_visible_context(context: Mapping[str, Any]) -> None:
    """Reject context containing privileged fields at any nesting depth."""

    expected = {
        "schema_version",
        "role",
        "task_id",
        "instruction",
        "session",
        "drones",
        "environment",
        "observation_contract",
    }
    if set(context) != expected:
        raise ValueError(
            f"agent context fields differ from schema: {sorted(set(context) ^ expected)}"
        )
    if context.get("schema_version") != CONTEXT_SCHEMA_VERSION:
        raise ValueError("unsupported agent context schema version")
    if context.get("role") != "AGENT":
        raise ValueError("agent context role must be AGENT")
    leaked = sorted(_find_keys(context, PRIVILEGED_SOURCE_FIELDS))
    if leaked:
        raise ValueError(f"agent context contains privileged fields: {leaked}")
    _nonempty_text(context.get("task_id"), "agent context task_id")
    _nonempty_text(context.get("instruction"), "agent context instruction")
    session = _require_mapping(context.get("session"), "agent context session")
    _reject_unknown_fields(session, set(SESSION_FIELDS), "agent context session")
    drones = context.get("drones")
    if not isinstance(drones, list) or not drones:
        raise ValueError("agent context drones must be a non-empty list")
    for index, drone in enumerate(drones):
        _reject_unknown_fields(
            _require_mapping(drone, f"agent context drone {index}"),
            set(DRONE_FIELDS),
            f"agent context drone {index}",
        )
    environment = _require_mapping(
        context.get("environment"),
        "agent context environment",
    )
    _reject_unknown_fields(
        environment,
        set(ENVIRONMENT_FIELDS),
        "agent context environment",
    )
    observation = _require_mapping(
        context.get("observation_contract"),
        "agent context observation_contract",
    )
    _reject_unknown_fields(
        observation,
        {
            "global_targets_visible",
            "global_obstacles_visible",
            "local_perception_required",
            "allowed_endpoints",
        },
        "agent context observation_contract",
    )


def privileged_noninterference_check(
    session: Mapping[str, Any],
    *,
    task_id: str,
    instruction: str,
) -> bool:
    """Prove privileged source-field values do not affect the projection."""

    baseline = project_agent_visible_context(
        session,
        task_id=task_id,
        instruction=instruction,
    )
    mutated = deepcopy(dict(session))
    _mutate_privileged_fields(mutated)
    candidate = project_agent_visible_context(
        mutated,
        task_id=task_id,
        instruction=instruction,
    )
    return candidate == baseline


def _project_fields(
    source: Mapping[str, Any],
    fields: tuple[str, ...],
) -> dict[str, Any]:
    return {
        field: deepcopy(source[field])
        for field in fields
        if field in source
    }


def _find_keys(value: Any, forbidden: frozenset[str]) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in forbidden:
                found.add(str(key))
            found.update(_find_keys(child, forbidden))
    elif isinstance(value, list):
        for child in value:
            found.update(_find_keys(child, forbidden))
    return found


def _mutate_privileged_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key in list(value):
            if key in PRIVILEGED_SOURCE_FIELDS:
                value[key] = {"sentinel": "privileged-value-must-not-affect-context"}
            else:
                _mutate_privileged_fields(value[key])
    elif isinstance(value, list):
        for child in value:
            _mutate_privileged_fields(child)


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _reject_unknown_fields(
    value: Mapping[str, Any],
    allowed: set[str],
    label: str,
) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"{label} contains fields outside the allowlist: {unknown}")


def _nonempty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()
