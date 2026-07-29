"""Freeze the deterministic MultiUAV endpoint and grounding contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_grounding_validator import (  # noqa: E402
    ACCEPTED_STAGE,
    ENDPOINT_SCHEMA_STAGE,
    ENDPOINT_SPECS,
    IDENTIFIER_STAGE,
    PARAMETER_STAGE,
    SAFETY_BOUNDS_STAGE,
)
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source_path = (
        ROOT / "src" / "shepherd_ai" / "multiuav_grounding_validator.py"
    )
    result = {
        "schema_version": 1,
        "valid": True,
        "endpoint_count": len(ENDPOINT_SPECS),
        "endpoint_contract": {
            endpoint: {
                "required_parameters": sorted(spec.required),
                "optional_parameters": sorted(spec.optional),
            }
            for endpoint, spec in sorted(ENDPOINT_SPECS.items())
        },
        "containment_order": [
            ENDPOINT_SCHEMA_STAGE,
            IDENTIFIER_STAGE,
            PARAMETER_STAGE,
            SAFETY_BOUNDS_STAGE,
            ACCEPTED_STAGE,
        ],
        "grounding_contract": {
            "recursive_waypoint_validation": True,
            "identifier_source": "exact_agent_visible_drone_id",
            "instruction_number_source": (
                "explicit_number_excluding_drone_or_uav_identifier_mentions"
            ),
            "context_numeric_sources": {
                "x": ["drone.position.x", "drone.home_position.x"],
                "y": ["drone.position.y", "drone.home_position.y"],
                "z": ["drone.position.z", "drone.home_position.z"],
                "altitude": [
                    "drone.position.z",
                    "drone.home_position.z",
                ],
                "heading": ["drone.heading"],
                "distance": [],
                "duration": [],
            },
            "registered_derivations": {
                "compass_heading_degrees": {
                    "north": 0,
                    "northeast": 45,
                    "east": 90,
                    "southeast": 135,
                    "south": 180,
                    "southwest": 225,
                    "west": 270,
                    "northwest": 315,
                }
            },
            "message_rule": "normalized_instruction_substring",
            "provenance_recorded_per_grounded_leaf": True,
            "limits_are_not_grounding_evidence": True,
        },
        "safety_bounds": {
            "x": "agent_visible_session.canvas_width",
            "y": "agent_visible_session.canvas_height",
            "z": "selected_agent_visible_drone.max_altitude",
            "altitude": "selected_agent_visible_drone.max_altitude",
            "heading": "[0,360)",
            "distance": "positive",
            "duration": "positive",
        },
        "hidden_reference_inputs_used": False,
        "model_invoked": False,
        "source_code_sha256": {
            "multiuav_grounding_validator.py": sha256_file(source_path),
        },
        "claim_status": (
            "deterministic_structural_and_visible_evidence_validation_"
            "implemented_not_mission_success"
        ),
        "limitations": [
            (
                "The validator establishes endpoint shape, visible-evidence "
                "grounding, and static bounds only."
            ),
            (
                "It does not establish instruction fidelity, dynamic "
                "feasibility, collision avoidance, execution success, or "
                "mission success."
            ),
            (
                "Equal visible numeric values can remain semantically "
                "ambiguous within a compatible parameter class."
            ),
            "No revised-study model was loaded or invoked.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
