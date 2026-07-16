import json
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations
from shepherd_ai.safety import load_safety_policy
from shepherd_ai.week8_pipeline import prepare_week8_mission


class Week8PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.locations = load_map_locations(ROOT / "datasets/maps/shepherd_test_map_v1.csv")
        cls.fleet = json.loads(
            (ROOT / "datasets/drones/week5_three_drone_fleet_v1.json").read_text(
                encoding="utf-8"
            )
        )
        cls.policy = load_safety_policy(ROOT / "datasets/safety/week7_safety_policy_v1.json")

    def test_exact_roadmap_scenario_stops_on_distinct_grounded_references(self) -> None:
        result = prepare_week8_mission(
            "Send two drones north to inspect crops and one drone east to inspect irrigation.",
            locations=self.locations,
            fleet_payload=self.fleet,
            safety_policy=self.policy,
        )

        self.assertEqual(result["status"], "clarification_required")
        self.assertEqual(result["decomposition"]["total_requested_drones"], 3)
        self.assertEqual(result["blocking_clauses"], ["clause_002"])
        self.assertEqual(result["schedule"], None)
        self.assertIn(
            "clause_002_distinct_location_and_target",
            result["issues"],
        )

    def test_map_consistent_control_reaches_three_assignment_preflight(self) -> None:
        result = prepare_week8_mission(
            "Send two drones north to inspect crops and one drone to inspect irrigation.",
            locations=self.locations,
            fleet_payload=self.fleet,
            safety_policy=self.policy,
        )

        self.assertEqual(result["status"], "awaiting_required_week8_evidence")
        self.assertEqual(len(result["plans"]), 2)
        self.assertEqual(len(result["schedule"]["assignments"]), 3)
        self.assertEqual(result["safety_report"]["status"], "approved")
        self.assertEqual(
            result["missing_evidence"],
            ["exact_scenario_asr_prediction", "mission_image_manifest", "mission_vision_results"],
        )

    def test_single_clause_is_supported_without_inventing_more_tasks(self) -> None:
        result = prepare_week8_mission(
            "Send two drones north to inspect crops.",
            locations=self.locations,
            fleet_payload=self.fleet,
            safety_policy=self.policy,
        )

        self.assertEqual(len(result["schedule"]["assignments"]), 2)
        self.assertEqual(result["decomposition"]["status"], "single_clause")


if __name__ == "__main__":
    unittest.main()
