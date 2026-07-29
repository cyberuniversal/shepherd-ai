import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
AUDIT_SCRIPT = ROOT / "scripts" / "audit_multiuav_grounding_contract.py"

from shepherd_ai.multiuav_context import project_agent_visible_context  # noqa: E402
from shepherd_ai.multiuav_grounding_validator import (  # noqa: E402
    ACCEPTED_STAGE,
    ENDPOINT_SCHEMA_STAGE,
    IDENTIFIER_STAGE,
    PARAMETER_STAGE,
    SAFETY_BOUNDS_STAGE,
    validate_grounded_plan,
)
from shepherd_ai.multiuav_plan_contract import (  # noqa: E402
    parse_strict_model_output,
)


def _session() -> dict:
    return {
        "id": "session-1",
        "task_type": "area_search",
        "canvas_width": 100,
        "canvas_height": 80,
        "is_distance_3d": True,
        "status": "active",
        "drones": [
            {
                "id": "drone-1",
                "name": "Drone 1",
                "status": "idle",
                "position": {"x": 5, "y": 6, "z": 0},
                "heading": 0,
                "max_altitude": 50,
                "home_position": {"x": 5, "y": 6, "z": 0},
            },
            {
                "id": "drone-2",
                "name": "Drone 2",
                "status": "idle",
                "position": {"x": 20, "y": 30, "z": 0},
                "heading": 90,
                "max_altitude": 60,
                "home_position": {"x": 20, "y": 30, "z": 0},
            },
        ],
        "environment": {
            "id": "environment-1",
            "name": "Clear",
            "weather": "clear",
        },
    }


def _context(instruction: str) -> dict:
    return project_agent_visible_context(
        _session(),
        task_id="task-1",
        instruction=instruction,
    )


def _output(decision: str, plan: list[dict]) -> object:
    parsed = parse_strict_model_output(
        json.dumps(
            {
                "decision": decision,
                "reason": "Test fixture.",
                "clarification_question": (
                    "Which UAV?" if decision == "CLARIFY" else None
                ),
                "api_plan": plan,
            }
        )
    )
    if parsed.parsed is None:
        raise AssertionError(parsed.to_dict())
    return parsed.parsed


class MultiUavGroundingValidatorTests(unittest.TestCase):
    def test_valid_takeoff_is_grounded_in_instruction_and_context(self) -> None:
        output = _output(
            "EXECUTE",
            [
                {
                    "endpoint": "/drones/{id}/command/take_off",
                    "parameters": {"id": "drone-1", "altitude": 20},
                }
            ],
        )

        result = validate_grounded_plan(
            output,
            _context("Have Drone 1 take off to 20 meters."),
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.containment_stage, ACCEPTED_STAGE)
        self.assertEqual(result.validated_call_count, 1)
        self.assertEqual(
            [item.source_path for item in result.evidence],
            ["drones[0].id", "instruction[25:27]"],
        )

    def test_unknown_endpoint_is_contained_at_schema_stage(self) -> None:
        output = _output(
            "EXECUTE",
            [
                {
                    "endpoint": "/admin/teleport",
                    "parameters": {"id": "drone-1"},
                }
            ],
        )

        result = validate_grounded_plan(output, _context("Move Drone 1."))

        self.assertFalse(result.valid)
        self.assertEqual(result.containment_stage, ENDPOINT_SCHEMA_STAGE)
        self.assertEqual(result.issues[0].code, "endpoint_not_allowed")

    def test_missing_or_unknown_parameters_are_schema_failures(self) -> None:
        output = _output(
            "EXECUTE",
            [
                {
                    "endpoint": "/drones/{id}/command/move_to",
                    "parameters": {"id": "drone-1", "x": 10, "speed": 4},
                }
            ],
        )

        result = validate_grounded_plan(
            output,
            _context("Move Drone 1 to 10, 20."),
        )

        self.assertEqual(result.containment_stage, ENDPOINT_SCHEMA_STAGE)
        self.assertEqual(
            {issue.code for issue in result.issues},
            {"missing_parameters", "unknown_parameters"},
        )

    def test_unknown_drone_is_contained_before_parameter_grounding(self) -> None:
        output = _output(
            "EXECUTE",
            [
                {
                    "endpoint": "/drones/{id}/command/take_off",
                    "parameters": {"id": "invented-drone", "altitude": 20},
                }
            ],
        )

        result = validate_grounded_plan(
            output,
            _context("Take off to 20 meters."),
        )

        self.assertEqual(result.containment_stage, IDENTIFIER_STAGE)
        self.assertEqual(result.issues[0].path, "api_plan[0].parameters.id")

    def test_hallucinated_numeric_value_is_contained(self) -> None:
        output = _output(
            "EXECUTE",
            [
                {
                    "endpoint": "/drones/{id}/command/take_off",
                    "parameters": {"id": "drone-1", "altitude": 33},
                }
            ],
        )

        result = validate_grounded_plan(
            output,
            _context("Have Drone 1 take off to 20 meters."),
        )

        self.assertEqual(result.containment_stage, PARAMETER_STAGE)
        self.assertEqual(result.issues[0].code, "ungrounded_numeric_value")

    def test_drone_number_does_not_ground_an_unstated_parameter(self) -> None:
        output = _output(
            "EXECUTE",
            [
                {
                    "endpoint": "/drones/{id}/command/take_off",
                    "parameters": {"id": "drone-1", "altitude": 1},
                }
            ],
        )

        result = validate_grounded_plan(
            output,
            _context("Have Drone 1 take off."),
        )

        self.assertEqual(result.containment_stage, PARAMETER_STAGE)

    def test_limit_values_are_not_treated_as_grounding_evidence(self) -> None:
        output = _output(
            "EXECUTE",
            [
                {
                    "endpoint": "/drones/{id}/command/take_off",
                    "parameters": {"id": "drone-1", "altitude": 50},
                }
            ],
        )

        result = validate_grounded_plan(
            output,
            _context("Have Drone 1 take off."),
        )

        self.assertEqual(result.containment_stage, PARAMETER_STAGE)

    def test_visible_coordinates_are_parameter_compatible_evidence(self) -> None:
        output = _output(
            "EXECUTE",
            [
                {
                    "endpoint": "/drones/{id}/command/move_to",
                    "parameters": {"id": "drone-1", "x": 20, "y": 30},
                }
            ],
        )

        result = validate_grounded_plan(
            output,
            _context("Move Drone 1 to Drone 2's current position."),
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.evidence[1].source_path, "drones[1].position.x")
        self.assertEqual(result.evidence[2].source_path, "drones[1].position.y")

    def test_waypoints_are_checked_recursively(self) -> None:
        output = _output(
            "EXECUTE",
            [
                {
                    "endpoint": "/drones/{id}/command/move_along_path",
                    "parameters": {
                        "id": "drone-1",
                        "waypoints": [
                            {"x": 10, "y": 20, "z": 15},
                            {"x": 30, "y": 40, "z": 15},
                        ],
                    },
                }
            ],
        )

        result = validate_grounded_plan(
            output,
            _context("Fly through (10,20,15) and (30,40,15)."),
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.validated_parameter_leaf_count, 7)
        self.assertEqual(result.evidence[-1].parameter, "z")

    def test_compass_heading_is_registered_derivation(self) -> None:
        output = _output(
            "EXECUTE",
            [
                {
                    "endpoint": "/drones/{id}/command/move_towards",
                    "parameters": {
                        "id": "drone-1",
                        "distance": 25,
                        "heading": 0,
                    },
                }
            ],
        )

        result = validate_grounded_plan(
            output,
            _context("Move Drone 1 north for 25 meters."),
        )

        self.assertTrue(result.valid)
        self.assertEqual(
            result.evidence[-1].basis,
            "registered_compass_heading",
        )

    def test_out_of_bounds_value_is_contained_after_grounding(self) -> None:
        output = _output(
            "EXECUTE",
            [
                {
                    "endpoint": "/drones/{id}/command/move_to",
                    "parameters": {
                        "id": "drone-1",
                        "x": 120,
                        "y": 20,
                        "z": 15,
                    },
                }
            ],
        )

        result = validate_grounded_plan(
            output,
            _context("Move Drone 1 to (120, 20, 15)."),
        )

        self.assertEqual(result.containment_stage, SAFETY_BOUNDS_STAGE)
        self.assertEqual(result.issues[0].path, "api_plan[0].parameters.x")

    def test_broadcast_message_must_be_visible_in_instruction(self) -> None:
        output = _output(
            "EXECUTE",
            [
                {
                    "endpoint": "/drones/{id}/command/broadcast",
                    "parameters": {
                        "id": "drone-1",
                        "message": "mission complete",
                    },
                }
            ],
        )

        accepted = validate_grounded_plan(
            output,
            _context("Have Drone 1 broadcast mission complete."),
        )
        rejected = validate_grounded_plan(
            output,
            _context("Have Drone 1 broadcast a status update."),
        )

        self.assertTrue(accepted.valid)
        self.assertEqual(rejected.containment_stage, PARAMETER_STAGE)

    def test_nonexecute_decision_has_no_plan_to_ground(self) -> None:
        result = validate_grounded_plan(
            _output("CLARIFY", []),
            _context("Inspect the area."),
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.validated_call_count, 0)

    def test_audit_cli_freezes_contract_without_hidden_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "audit.json"
            subprocess.run(
                [
                    sys.executable,
                    str(AUDIT_SCRIPT),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            audit = json.loads(output.read_text(encoding="utf-8"))

        self.assertTrue(audit["valid"])
        self.assertEqual(audit["endpoint_count"], 11)
        self.assertFalse(audit["hidden_reference_inputs_used"])
        self.assertFalse(audit["model_invoked"])
        self.assertTrue(
            audit["grounding_contract"]["provenance_recorded_per_grounded_leaf"]
        )


if __name__ == "__main__":
    unittest.main()
