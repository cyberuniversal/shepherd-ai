import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations  # noqa: E402
from shepherd_ai.integration import run_integrated_workflow  # noqa: E402
from shepherd_ai.safety import load_safety_policy  # noqa: E402


MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
FLEET_PATH = ROOT / "datasets" / "drones" / "week5_three_drone_fleet_v1.json"
POLICY_PATH = ROOT / "datasets" / "safety" / "week7_safety_policy_v1.json"


def _inputs():
    return (
        load_map_locations(MAP_PATH),
        json.loads(FLEET_PATH.read_text(encoding="utf-8")),
        load_safety_policy(POLICY_PATH),
    )


class IntegrationTests(unittest.TestCase):
    def test_safe_command_reaches_safety_approved_state(self) -> None:
        locations, fleet, policy = _inputs()

        result = run_integrated_workflow(
            "Send two drones north and scan the crops.",
            locations=locations,
            fleet_payload=fleet,
            safety_policy=policy,
            mission_altitude_m=30.0,
        )

        self.assertEqual(result.status, "ready_for_simulated_execution")
        self.assertEqual(result.safety_report["status"], "approved")
        self.assertEqual(result.schedule["metrics"]["assigned_tasks"], 2)
        self.assertEqual(result.feedback["latest_status"], "safety_approved")
        self.assertEqual(len(result.simulated_status_updates), 4)
        self.assertEqual(result.simulated_status_updates[-1]["status"], "task_completed")

    def test_ambiguous_command_stops_for_clarification(self) -> None:
        locations, fleet, policy = _inputs()

        result = run_integrated_workflow(
            "Check if there is any traffic on the road.",
            locations=locations,
            fleet_payload=fleet,
            safety_policy=policy,
        )

        self.assertEqual(result.status, "clarification_required")
        self.assertTrue(result.clarification_report["blocks_planning"])
        self.assertIsNone(result.mission_plan)
        self.assertIsNone(result.schedule)
        self.assertIsNone(result.safety_report)
        self.assertEqual(result.simulated_status_updates, ())

    def test_restricted_target_is_rejected_before_execution(self) -> None:
        locations, fleet, policy = _inputs()

        result = run_integrated_workflow(
            "Check the equipment in the maintenance yard.",
            locations=locations,
            fleet_payload=fleet,
            safety_policy=policy,
        )

        self.assertEqual(result.status, "safety_rejected")
        self.assertFalse(result.safety_report["safe_to_execute"])
        self.assertEqual(result.feedback["latest_status"], "safety_rejected")
        self.assertEqual(result.simulated_status_updates, ())

    def test_command_altitude_ceiling_is_enforced(self) -> None:
        locations, fleet, policy = _inputs()

        result = run_integrated_workflow(
            "Inspect the greenhouse and keep them below twenty meters.",
            locations=locations,
            fleet_payload=fleet,
            safety_policy=policy,
            mission_altitude_m=30.0,
        )

        self.assertEqual(result.status, "safety_rejected")
        self.assertEqual(result.safety_report["command_altitude_ceiling_m"], 20.0)
        altitude_check = next(
            check
            for check in result.safety_report["assignment_results"][0]["checks"]
            if check["category"] == "altitude"
        )
        self.assertEqual(altitude_check["reason"], "altitude_violates_command_ceiling")


if __name__ == "__main__":
    unittest.main()
