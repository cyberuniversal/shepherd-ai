"""Create human-collection packets for Week 3 grounding benchmarks."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from shepherd_ai.grounding import MapLocation


@dataclass(frozen=True)
class HumanGroundingSlot:
    """One blank human-writing slot for a future grounding benchmark."""

    id: str
    label_status: str
    split: str
    source: str
    data_type: str
    instruction: str
    text: str
    expected_grounding: dict[str, dict[str, Any]]
    map_focus: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "label_status": self.label_status,
            "split": self.split,
            "source": self.source,
            "data_type": self.data_type,
            "instruction": self.instruction,
            "text": self.text,
            "expected_grounding": self.expected_grounding,
        }
        if self.map_focus is not None:
            payload["map_focus"] = self.map_focus
        return payload


def build_human_grounding_packet(
    locations: list[MapLocation],
    *,
    record_prefix: str = "human_ground",
    source: str = "manual_week3_grounding_benchmark_v1",
    split: str = "human_holdout_candidate",
) -> list[HumanGroundingSlot]:
    """Build blank human-command slots covering map records and failure modes."""

    slots: list[HumanGroundingSlot] = []
    for index, location in enumerate(locations, start=1):
        slots.append(
            HumanGroundingSlot(
                id=f"{record_prefix}_{index:03d}",
                label_status="needs_human_written_command",
                split=split,
                source=source,
                data_type="human_grounding_prompt_slot",
                instruction=(
                    "Write one natural mission command that refers to this map record. "
                    "Use your own wording; do not copy the example aliases unless needed."
                ),
                text="",
                expected_grounding={
                    "target": {
                        "status": "grounded",
                        "location_id": location.id,
                    }
                },
                map_focus={
                    "location_id": location.id,
                    "name": location.name,
                    "category": location.category,
                    "map_role": location.map_role,
                    "aliases": list(location.aliases),
                },
            )
        )

    next_index = len(slots) + 1
    slots.extend(
        [
            HumanGroundingSlot(
                id=f"{record_prefix}_{next_index:03d}",
                label_status="needs_human_written_command",
                split=split,
                source=source,
                data_type="human_grounding_prompt_slot",
                instruction=(
                    "Write one natural mission command that intentionally uses the ambiguous term 'road'."
                ),
                text="",
                expected_grounding={
                    "location": {
                        "status": "ambiguous",
                        "location_id": None,
                        "candidate_ids": ["loc_service_road", "loc_main_road"],
                    }
                },
                map_focus=None,
            ),
            HumanGroundingSlot(
                id=f"{record_prefix}_{next_index + 1:03d}",
                label_status="needs_human_written_command",
                split=split,
                source=source,
                data_type="human_grounding_prompt_slot",
                instruction=(
                    "Write one natural mission command that refers to an object not present in the map, "
                    "such as a vehicle, animal, person, or temporary object."
                ),
                text="",
                expected_grounding={
                    "target": {
                        "status": "unresolved",
                        "location_id": None,
                    }
                },
                map_focus=None,
            ),
        ]
    )
    return slots


def render_human_grounding_packet_markdown(slots: list[HumanGroundingSlot]) -> str:
    """Render a human-editable Markdown packet."""

    lines = [
        "# Week 3 Human Grounding Benchmark Packet",
        "",
        "This packet is for collecting human-written grounding commands. Blank slots are not benchmark data until a human fills the `text` field and the completed JSONL is validated.",
        "",
        "Rules:",
        "",
        "- Keep one command per slot.",
        "- Do not mark a blank slot as human-collected data.",
        "- Preserve the expected grounding fields unless the written command truly changes the intended reference.",
        "- Synthetic examples and model-generated text must not be copied into this packet as human-written data.",
        "",
    ]
    for slot in slots:
        payload = slot.to_dict()
        lines.extend(
            [
                f"## {slot.id}",
                "",
                f"- Instruction: {slot.instruction}",
                f"- Expected grounding: `{json.dumps(payload['expected_grounding'], sort_keys=True)}`",
                f"- Text: ",
                "",
            ]
        )
    return "\n".join(lines)
