"""Clarification reports for unresolved or ambiguous grounding results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping

from shepherd_ai.grounding import GroundedIntent, GroundedReference, MapLocation


@dataclass(frozen=True)
class ClarificationOption:
    """One operator-selectable candidate for an ambiguous grounding phrase."""

    location_id: str
    name: str
    category: str
    map_role: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClarificationRequest:
    """One clarification or review item produced from grounding."""

    field: str
    phrase: str | None
    reason: str
    question: str
    options: tuple[ClarificationOption, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "phrase": self.phrase,
            "reason": self.reason,
            "question": self.question,
            "options": [option.to_dict() for option in self.options],
        }


@dataclass(frozen=True)
class ClarificationReport:
    """Operator-facing report for grounding states that need review."""

    command_text: str
    ready_for_planning: bool
    blocks_planning: bool
    requests: tuple[ClarificationRequest, ...] = field(default_factory=tuple)
    issues: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_text": self.command_text,
            "ready_for_planning": self.ready_for_planning,
            "blocks_planning": self.blocks_planning,
            "requests": [request.to_dict() for request in self.requests],
            "issues": list(self.issues),
        }


def build_clarification_report(grounded_intent: GroundedIntent) -> ClarificationReport:
    """Build clarification prompts from a grounded intent.

    This function does not answer the clarification. It only turns ambiguous or
    unresolved grounding records into explicit operator-facing questions.
    """

    requests = tuple(
        request
        for reference in grounded_intent.references
        for request in [_request_for_reference(reference)]
        if request is not None
    )
    blocks_planning = _blocks_planning(grounded_intent, requests)
    return ClarificationReport(
        command_text=str(grounded_intent.intent.get("text", "")),
        ready_for_planning=grounded_intent.ready_for_planning,
        blocks_planning=blocks_planning,
        requests=requests,
        issues=grounded_intent.issues,
    )


def apply_clarification_choices(
    grounded_intent: GroundedIntent,
    choices: Mapping[str, str],
    *,
    locations: Iterable[MapLocation] | None = None,
) -> GroundedIntent:
    """Apply explicit operator location choices to a grounded intent.

    Choices are keyed by reference field, for example
    ``{"location": "loc_service_road"}``. Ambiguous references may only be
    resolved to one of their candidates. Unresolved references may be resolved
    only when ``locations`` is provided and the selected id exists in that map.
    """

    location_index = {location.id: location for location in locations or ()}
    updated_references = tuple(
        _apply_choice_to_reference(reference, choices, location_index)
        for reference in grounded_intent.references
    )
    return _grounded_intent_from_references(grounded_intent.intent, updated_references)


def _request_for_reference(reference: GroundedReference) -> ClarificationRequest | None:
    if reference.status == "ambiguous":
        phrase = reference.phrase or ""
        return ClarificationRequest(
            field=reference.field,
            phrase=reference.phrase,
            reason="ambiguous_map_reference",
            question=f"Which map location should '{phrase}' refer to for {reference.field}?",
            options=tuple(
                ClarificationOption(
                    location_id=candidate.id,
                    name=candidate.name,
                    category=candidate.category,
                    map_role=candidate.map_role,
                )
                for candidate in reference.candidates
            ),
        )

    if reference.status == "unresolved":
        phrase = reference.phrase or ""
        return ClarificationRequest(
            field=reference.field,
            phrase=reference.phrase,
            reason="unresolved_map_reference",
            question=(
                f"No map record matched '{phrase}' for {reference.field}. "
                "Provide a known map alias or add the location to the map dataset."
            ),
        )

    return None


def _apply_choice_to_reference(
    reference: GroundedReference,
    choices: Mapping[str, str],
    location_index: Mapping[str, MapLocation],
) -> GroundedReference:
    if reference.field not in choices:
        return reference

    selected_id = choices[reference.field]
    if reference.status == "ambiguous":
        candidate_index = {candidate.id: candidate for candidate in reference.candidates}
        if selected_id not in candidate_index:
            valid = ", ".join(sorted(candidate_index))
            raise ValueError(
                f"choice for {reference.field} must be one of the ambiguous candidates: {valid}"
            )
        return GroundedReference(
            field=reference.field,
            phrase=reference.phrase,
            status="grounded",
            location=candidate_index[selected_id],
            confidence=1.0,
            note="operator_selected_ambiguous_candidate",
        )

    if reference.status == "unresolved":
        if selected_id not in location_index:
            raise ValueError(f"choice for {reference.field} does not exist in map: {selected_id}")
        return GroundedReference(
            field=reference.field,
            phrase=reference.phrase,
            status="grounded",
            location=location_index[selected_id],
            confidence=1.0,
            note="operator_selected_location_for_unresolved_reference",
        )

    if reference.status == "not_provided":
        if selected_id not in location_index:
            raise ValueError(f"choice for {reference.field} does not exist in map: {selected_id}")
        return GroundedReference(
            field=reference.field,
            phrase=reference.phrase,
            status="grounded",
            location=location_index[selected_id],
            confidence=1.0,
            note="operator_selected_location_for_missing_reference",
        )

    if reference.status == "grounded":
        if reference.location is None or reference.location.id != selected_id:
            raise ValueError(f"choice for already grounded {reference.field} conflicts with current location")
        return reference

    raise ValueError(f"unsupported grounding status for {reference.field}: {reference.status}")


def _grounded_intent_from_references(
    intent: dict[str, Any],
    references: tuple[GroundedReference, ...],
) -> GroundedIntent:
    issues = tuple(_issues_for_references(references))
    issues = issues + tuple(_map_role_issues(references))
    has_grounded_reference = any(reference.status == "grounded" for reference in references)
    has_ambiguity = any(reference.status == "ambiguous" for reference in references)
    ready_for_planning = has_grounded_reference and not has_ambiguity
    if not has_grounded_reference:
        issues = issues + ("no_grounded_map_reference",)
    return GroundedIntent(
        intent=dict(intent),
        references=references,
        ready_for_planning=ready_for_planning,
        issues=issues,
    )


def _issues_for_references(references: Iterable[GroundedReference]) -> list[str]:
    issues: list[str] = []
    for reference in references:
        if reference.status == "ambiguous":
            issues.append(f"{reference.field}_ambiguous")
        elif reference.status == "unresolved":
            issues.append(f"{reference.field}_unresolved")
    return issues


def _map_role_issues(references: Iterable[GroundedReference]) -> list[str]:
    issues: list[str] = []
    for reference in references:
        if reference.status != "grounded" or reference.location is None:
            continue
        if not reference.location.flyable:
            issues.append(f"{reference.field}_not_flyable")
        if reference.location.requires_clearance:
            issues.append(f"{reference.field}_requires_clearance")
    return issues


def _blocks_planning(
    grounded_intent: GroundedIntent,
    requests: tuple[ClarificationRequest, ...],
) -> bool:
    if any(request.reason == "ambiguous_map_reference" for request in requests):
        return True
    if "no_grounded_map_reference" in grounded_intent.issues:
        return True
    return not grounded_intent.ready_for_planning
