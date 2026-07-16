"""Stateful operator clarification dialogue for grounded mission commands."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from shepherd_ai.grounding import GroundedIntent, MapLocation
from shepherd_ai.grounding_clarification import (
    apply_clarification_choices,
    build_clarification_report,
)


TERMINAL_STATES = {"cancelled", "confirmed", "timed_out"}


@dataclass(frozen=True)
class ClarificationEvent:
    sequence: int
    event_type: str
    status: str
    message: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ClarificationSession:
    """Validate operator choices while preserving the original command and history."""

    def __init__(
        self,
        grounded_intent: GroundedIntent,
        locations: Iterable[MapLocation],
    ) -> None:
        self._original = grounded_intent
        self._resolved = grounded_intent
        self._locations = tuple(locations)
        self._report = build_clarification_report(grounded_intent)
        self._status = (
            "awaiting_response" if self._report.blocks_planning else "awaiting_confirmation"
        )
        self._events: list[ClarificationEvent] = []
        self._record(
            "clarification_requested" if self._report.blocks_planning else "confirmation_requested",
            (
                "Operator clarification is required before planning."
                if self._report.blocks_planning
                else "Grounding is ready and awaits operator confirmation."
            ),
            {"request_count": len(self._report.requests)},
        )

    def submit_choices(self, choices: Mapping[str, str]) -> dict[str, Any]:
        """Apply an operator response and retain invalid responses as evidence."""

        self._require_status("awaiting_response")
        try:
            candidate = apply_clarification_choices(
                self._resolved,
                choices,
                locations=self._locations,
            )
        except ValueError as exc:
            self._record(
                "response_rejected",
                "The clarification response did not match the available map choices.",
                {"choices": dict(choices), "error": str(exc)},
            )
            return {"accepted": False, "error": str(exc), "status": self._status}

        self._resolved = candidate
        self._report = build_clarification_report(candidate)
        self._status = (
            "awaiting_response" if self._report.blocks_planning else "awaiting_confirmation"
        )
        self._record(
            "response_accepted",
            (
                "The response was accepted; additional clarification is required."
                if self._report.blocks_planning
                else "The response was accepted and awaits explicit confirmation."
            ),
            {"choices": dict(choices), "remaining_requests": len(self._report.requests)},
        )
        return {"accepted": True, "error": None, "status": self._status}

    def confirm(self) -> GroundedIntent:
        """Confirm the resolved grounding for downstream planning."""

        self._require_status("awaiting_confirmation")
        self._status = "confirmed"
        self._record(
            "operator_confirmed",
            "Operator confirmed the grounded mission command.",
            {},
        )
        return self._resolved

    def cancel(self, reason: str) -> None:
        """Cancel the clarification instead of silently selecting a candidate."""

        if self._status in TERMINAL_STATES:
            raise ValueError(f"clarification session is already terminal: {self._status}")
        self._status = "cancelled"
        self._record(
            "operator_cancelled",
            "Operator cancelled the clarification session.",
            {"reason": reason},
        )

    def timeout(self) -> None:
        """Close an unanswered session without treating it as resolved."""

        if self._status in TERMINAL_STATES:
            raise ValueError(f"clarification session is already terminal: {self._status}")
        self._status = "timed_out"
        self._record(
            "clarification_timed_out",
            "The clarification session timed out without confirmation.",
            {},
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "mode": "stateful_multi_turn",
            "status": self._status,
            "original_command": str(self._original.intent.get("text", "")),
            "current_report": self._report.to_dict(),
            "resolved_grounded_intent": self._resolved.to_dict(),
            "events": [event.to_dict() for event in self._events],
        }

    def _record(
        self,
        event_type: str,
        message: str,
        details: dict[str, Any],
    ) -> None:
        self._events.append(
            ClarificationEvent(
                sequence=len(self._events) + 1,
                event_type=event_type,
                status=self._status,
                message=message,
                details=details,
            )
        )

    def _require_status(self, expected: str) -> None:
        if self._status != expected:
            raise ValueError(
                f"clarification state must be {expected}, found {self._status}"
            )
