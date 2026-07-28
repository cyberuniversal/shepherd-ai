"""Frozen recoverability rules for controlled MultiUAV interventions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Mapping, Sequence


POLICY_VERSION = 1

REQUIRES_OPERATOR_FACTS = frozenset(
    {
        "explicit_drone_identity",
        "minimum_drone_count",
        "destination_coordinate",
        "waypoint_coordinate",
        "altitude",
        "movement_direction",
        "movement_distance",
        "action_duration",
        "message_payload",
        "communication_recipient",
        "target_reference",
        "formation_assignment",
        "coverage_threshold",
    }
)
INITIAL_CONTEXT_FACTS = frozenset(
    {
        "drone_runtime_id",
        "drone_battery_level",
        "drone_status",
        "drone_position",
        "environment_state",
    }
)
LOCAL_OBSERVATION_FACTS = {
    "target_runtime_id": "GET /drones/{id}/nearby/targets",
    "target_runtime_position": "GET /drones/{id}/nearby/targets",
    "obstacle_geometry": "GET /drones/{id}/nearby/obstacles",
}
PLANNER_RESPONSIBILITY_FACTS = frozenset(
    {
        "generic_drone_assignment",
        "api_endpoint_selection",
        "route",
        "intermediate_waypoint",
    }
)

_FACT_PATTERNS = {
    "explicit_drone_identity": re.compile(r"\bDrone\s+\d+\b", re.IGNORECASE),
    "minimum_drone_count": re.compile(
        r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+drones?\b",
        re.IGNORECASE,
    ),
    "waypoint_coordinate": re.compile(
        r"(?<!\w)\(?\d+(?:\.\d+)?\s*[, ]\s*\d+(?:\.\d+)?"
        r"(?:\s*[, ]\s*\d+(?:\.\d+)?)?\)?"
    ),
    "altitude": re.compile(r"\b\d+(?:\.\d+)?\s*(?:m|meters?)\b", re.IGNORECASE),
    "movement_direction": re.compile(
        r"\b(?:north|south|east|west|northeast|northwest|southeast|southwest)\b",
        re.IGNORECASE,
    ),
    "action_duration": re.compile(
        r"\b\d+(?:\.\d+)?\s*(?:seconds?|minutes?)\b",
        re.IGNORECASE,
    ),
    "target_reference": re.compile(
        r"\b(?:Fixed|Moving|Circle|Polygon)\s+Target\s+\d+\b"
        r"|\bWaypoint\s+\d+\b",
        re.IGNORECASE,
    ),
    "coverage_threshold": re.compile(r"\b\d+(?:\.\d+)?\s*%"),
}


@dataclass(frozen=True)
class RecoverabilityAssessment:
    fact_kind: str
    outcome: str
    expected_decision: str
    clarification_allowed: bool
    evidence_source: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResourceConflictAssessment:
    outcome: str
    expected_decision: str
    block_allowed: bool
    missing_required_drones: tuple[str, ...]
    required_count: int | None
    visible_drone_count: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_missing_fact(
    fact_kind: str,
    context: Mapping[str, Any],
    *,
    retained_reference: bool = False,
) -> RecoverabilityAssessment:
    """Classify a removed fact without consulting privileged source fields."""

    if fact_kind in REQUIRES_OPERATOR_FACTS:
        return RecoverabilityAssessment(
            fact_kind=fact_kind,
            outcome="requires_operator_clarification",
            expected_decision="CLARIFY",
            clarification_allowed=True,
            evidence_source="operator_instruction",
            reason="removed fact is an explicit mission requirement, not world state",
        )
    if fact_kind in INITIAL_CONTEXT_FACTS:
        return RecoverabilityAssessment(
            fact_kind=fact_kind,
            outcome="recoverable_from_initial_context",
            expected_decision="EXECUTE",
            clarification_allowed=False,
            evidence_source="agent_visible_context",
            reason="fact is present in the frozen initial AGENT context",
        )
    if fact_kind in LOCAL_OBSERVATION_FACTS:
        endpoint = LOCAL_OBSERVATION_FACTS[fact_kind]
        allowed = _allowed_endpoints(context)
        if retained_reference and endpoint in allowed:
            return RecoverabilityAssessment(
                fact_kind=fact_kind,
                outcome="recoverable_via_allowed_observation",
                expected_decision="EXECUTE",
                clarification_allowed=False,
                evidence_source=endpoint,
                reason=(
                    "a retained semantic reference can be resolved through an "
                    "allowed local-perception endpoint"
                ),
            )
        return RecoverabilityAssessment(
            fact_kind=fact_kind,
            outcome="requires_operator_clarification",
            expected_decision="CLARIFY",
            clarification_allowed=True,
            evidence_source="operator_instruction",
            reason=(
                "runtime fact cannot be resolved because no semantic reference "
                "or allowed observation path remains"
            ),
        )
    if fact_kind in PLANNER_RESPONSIBILITY_FACTS:
        return RecoverabilityAssessment(
            fact_kind=fact_kind,
            outcome="planner_responsibility",
            expected_decision="EXECUTE",
            clarification_allowed=False,
            evidence_source="validated_planning",
            reason="fact is a bounded planning choice rather than missing operator intent",
        )
    raise ValueError(f"unsupported recoverability fact kind: {fact_kind}")


def assess_resource_conflict(
    context: Mapping[str, Any],
    *,
    required_drone_references: Sequence[str] = (),
    required_count: int | None = None,
) -> ResourceConflictAssessment:
    """Allow BLOCK only when the AGENT cannot satisfy the fleet requirement."""

    drones = context.get("drones")
    if not isinstance(drones, list):
        raise ValueError("context drones must be a list")
    if required_count is not None and required_count < 1:
        raise ValueError("required_count must be positive")
    if not required_drone_references and required_count is None:
        raise ValueError("resource conflict requires exact drones or a count")

    visible_names: set[str] = set()
    for drone in drones:
        if not isinstance(drone, Mapping):
            raise ValueError("context drone must be an object")
        for field in ("id", "name"):
            value = drone.get(field)
            if isinstance(value, str) and value.strip():
                visible_names.add(_normalize_reference(value))
    required = tuple(
        sorted({_normalize_reference(value) for value in required_drone_references})
    )
    missing = tuple(value for value in required if value not in visible_names)
    count_shortfall = required_count is not None and len(drones) < required_count
    registration_allowed = "POST /drones" in _allowed_endpoints(context)

    if (missing or count_shortfall) and not registration_allowed:
        return ResourceConflictAssessment(
            outcome="irrecoverable_fleet_conflict",
            expected_decision="BLOCK",
            block_allowed=True,
            missing_required_drones=missing,
            required_count=required_count,
            visible_drone_count=len(drones),
            reason=(
                "required UAV identity or fleet cardinality is absent and the "
                "AGENT contract cannot register replacement UAVs"
            ),
        )
    return ResourceConflictAssessment(
        outcome="no_irrecoverable_fleet_conflict",
        expected_decision="EXECUTE",
        block_allowed=False,
        missing_required_drones=missing,
        required_count=required_count,
        visible_drone_count=len(drones),
        reason=(
            "the visible fleet can satisfy the requirement or the contract "
            "provides a recovery action"
        ),
    )


def detect_operator_fact_candidates(text: str) -> tuple[str, ...]:
    """Inventory conservative source-text candidates; do not generate labels."""

    if not isinstance(text, str) or not text.strip():
        raise ValueError("source instruction must be non-empty")
    return tuple(
        kind for kind, pattern in _FACT_PATTERNS.items() if pattern.search(text)
    )


def extract_explicit_drone_references(text: str) -> tuple[str, ...]:
    """Return normalized, ordered unique UAV names explicitly stated in text."""

    if not isinstance(text, str) or not text.strip():
        raise ValueError("source instruction must be non-empty")
    return tuple(
        dict.fromkeys(
            _normalize_reference(match.group(0))
            for match in _FACT_PATTERNS["explicit_drone_identity"].finditer(text)
        )
    )


def recoverability_policy_manifest() -> dict[str, Any]:
    return {
        "policy_version": POLICY_VERSION,
        "requires_operator_facts": sorted(REQUIRES_OPERATOR_FACTS),
        "initial_context_facts": sorted(INITIAL_CONTEXT_FACTS),
        "local_observation_facts": dict(sorted(LOCAL_OBSERVATION_FACTS.items())),
        "planner_responsibility_facts": sorted(PLANNER_RESPONSIBILITY_FACTS),
        "resource_conflict_rule": (
            "BLOCK only for absent explicitly required UAV identities or "
            "insufficient fleet cardinality when AGENT cannot register replacements"
        ),
        "excluded_resource_conflict_mutations": [
            "low_battery",
            "busy_status",
            "route_obstruction",
            "unknown_target_runtime_id_with_retained_reference",
        ],
    }


def _allowed_endpoints(context: Mapping[str, Any]) -> set[str]:
    observation = context.get("observation_contract")
    if not isinstance(observation, Mapping):
        raise ValueError("context observation_contract must be an object")
    endpoints = observation.get("allowed_endpoints")
    if not isinstance(endpoints, list) or not all(
        isinstance(endpoint, str) for endpoint in endpoints
    ):
        raise ValueError("context allowed_endpoints must be a list of strings")
    return set(endpoints)


def _normalize_reference(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("drone reference must be non-empty text")
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))
