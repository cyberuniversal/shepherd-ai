"""Ordered, serializable status feedback for the Week 7 workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from shepherd_ai.scheduling import ScheduleResult


@dataclass(frozen=True)
class FeedbackEvent:
    """One deterministic status update emitted by the integrated workflow."""

    sequence: int
    phase: str
    status: str
    message: str
    blocks_progress: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FeedbackLog:
    """Mutable event collector whose exported records remain deterministic."""

    def __init__(self) -> None:
        self._events: list[FeedbackEvent] = []

    def add(
        self,
        phase: str,
        status: str,
        message: str,
        *,
        blocks_progress: bool = False,
        details: dict[str, Any] | None = None,
    ) -> FeedbackEvent:
        event = FeedbackEvent(
            sequence=len(self._events) + 1,
            phase=phase,
            status=status,
            message=message,
            blocks_progress=blocks_progress,
            details=dict(details or {}),
        )
        self._events.append(event)
        return event

    @property
    def events(self) -> tuple[FeedbackEvent, ...]:
        return tuple(self._events)

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": [event.to_dict() for event in self._events],
            "latest_status": self._events[-1].status if self._events else None,
            "blocked": any(event.blocks_progress for event in self._events),
        }


def simulate_mission_status_updates(schedule: ScheduleResult) -> list[dict[str, Any]]:
    """Create schedule-timed status records without claiming actual execution."""

    updates: list[dict[str, Any]] = []
    for assignment in schedule.assignments:
        updates.extend(
            [
                {
                    "simulated_time_min": assignment.start_min,
                    "status": "task_started",
                    "task_id": assignment.task_id,
                    "drone_id": assignment.drone_id,
                },
                {
                    "simulated_time_min": assignment.end_min,
                    "status": "task_completed",
                    "task_id": assignment.task_id,
                    "drone_id": assignment.drone_id,
                },
            ]
        )
    updates.sort(
        key=lambda update: (
            float(update["simulated_time_min"]),
            0 if update["status"] == "task_started" else 1,
            str(update["task_id"]),
        )
    )
    return [
        {"sequence": index, "mode": "schedule_based_simulation", **update}
        for index, update in enumerate(updates, start=1)
    ]
