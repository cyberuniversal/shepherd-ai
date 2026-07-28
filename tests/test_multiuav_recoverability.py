from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_recoverability import (  # noqa: E402
    assess_missing_fact,
    assess_resource_conflict,
    detect_operator_fact_candidates,
    extract_explicit_drone_references,
)


def _context() -> dict:
    return {
        "drones": [
            {
                "id": "abc12345",
                "name": "Drone 1",
                "battery_level": 1.0,
                "status": "busy",
            },
            {
                "id": "def67890",
                "name": "Drone 2",
                "battery_level": 100.0,
                "status": "idle",
            },
        ],
        "observation_contract": {
            "allowed_endpoints": [
                "GET /drones",
                "GET /drones/{id}/nearby/targets",
                "GET /drones/{id}/nearby/obstacles",
                "POST /drones/{id}/command/charge",
            ]
        },
    }


class MultiUavRecoverabilityTests(unittest.TestCase):
    def test_removed_operator_altitude_requires_clarification(self) -> None:
        result = assess_missing_fact("altitude", _context())

        self.assertTrue(result.clarification_allowed)
        self.assertEqual(result.expected_decision, "CLARIFY")

    def test_named_target_runtime_id_is_observable_not_clarification(self) -> None:
        result = assess_missing_fact(
            "target_runtime_id",
            _context(),
            retained_reference=True,
        )

        self.assertFalse(result.clarification_allowed)
        self.assertEqual(result.expected_decision, "EXECUTE")
        self.assertEqual(result.outcome, "recoverable_via_allowed_observation")

    def test_target_without_reference_requires_clarification(self) -> None:
        result = assess_missing_fact(
            "target_runtime_id",
            _context(),
            retained_reference=False,
        )

        self.assertTrue(result.clarification_allowed)

    def test_route_and_generic_assignment_are_planner_responsibilities(self) -> None:
        for fact in ("route", "generic_drone_assignment"):
            with self.subTest(fact=fact):
                result = assess_missing_fact(fact, _context())
                self.assertEqual(result.outcome, "planner_responsibility")
                self.assertFalse(result.clarification_allowed)

    def test_low_battery_and_busy_status_do_not_create_block_label(self) -> None:
        result = assess_resource_conflict(
            _context(),
            required_drone_references=["Drone 1"],
        )

        self.assertFalse(result.block_allowed)
        self.assertEqual(result.expected_decision, "EXECUTE")

    def test_missing_exact_drone_is_irrecoverable(self) -> None:
        result = assess_resource_conflict(
            _context(),
            required_drone_references=["Drone 3"],
        )

        self.assertTrue(result.block_allowed)
        self.assertEqual(result.expected_decision, "BLOCK")
        self.assertEqual(result.missing_required_drones, ("drone 3",))

    def test_insufficient_fleet_cardinality_is_irrecoverable(self) -> None:
        result = assess_resource_conflict(_context(), required_count=3)

        self.assertTrue(result.block_allowed)
        self.assertEqual(result.expected_decision, "BLOCK")

    def test_candidate_detector_does_not_assign_labels(self) -> None:
        candidates = detect_operator_fact_candidates(
            "Drone 4 should take off to 12 meters and hover for 5 seconds."
        )

        self.assertEqual(
            candidates,
            ("explicit_drone_identity", "altitude", "action_duration"),
        )

    def test_explicit_drone_references_are_normalized_and_deduplicated(self) -> None:
        self.assertEqual(
            extract_explicit_drone_references(
                "Drone 4 follows Drone 2, then Drone 4 hovers."
            ),
            ("drone 4", "drone 2"),
        )


if __name__ == "__main__":
    unittest.main()
