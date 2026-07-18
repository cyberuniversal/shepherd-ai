import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations
from shepherd_ai.interactive_demo import InteractiveMissionDemo
from shepherd_ai.safety import load_safety_policy


class InteractiveMissionDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        locations = load_map_locations(ROOT / "datasets/maps/shepherd_test_map_v1.csv")
        fleet = json.loads(
            (ROOT / "datasets/drones/week5_three_drone_fleet_v1.json").read_text(
                encoding="utf-8"
            )
        )
        policy = load_safety_policy(ROOT / "datasets/safety/week7_safety_policy_v1.json")
        cls.demo = InteractiveMissionDemo(locations, fleet, policy)

    def test_exact_scenario_requests_grounding_clarification(self) -> None:
        result = self.demo.run(
            "Send two drones north to inspect crops and one drone east to inspect irrigation."
        )

        self.assertEqual(result["status"], "clarification_required")
        self.assertEqual(len(result["clarifications"]), 1)
        clarification = result["clarifications"][0]
        self.assertEqual(clarification["clause_id"], "clause_002")
        self.assertEqual(
            [option["location_id"] for option in clarification["options"]],
            ["loc_east_field", "loc_irrigation_canal"],
        )
        self.assertIsNone(result["simulation"])

    def test_resolution_runs_new_three_drone_simulation(self) -> None:
        result = self.demo.run(
            "Send two drones north to inspect crops and one drone east to inspect irrigation.",
            grounding_resolutions={"clause_002": "loc_east_field"},
        )

        self.assertEqual(result["status"], "simulation_ready")
        self.assertEqual(result["simulation"]["status"], "completed")
        self.assertEqual(result["simulation"]["assignment_count"], 3)
        self.assertEqual(result["simulation"]["supervision"]["mission_status"], "completed")
        self.assertEqual(result["research_status"], "missing_required_week8_evidence")

    def test_different_prompt_produces_different_mission(self) -> None:
        result = self.demo.run("Send one drone to inspect the greenhouse.")

        self.assertEqual(result["status"], "simulation_ready")
        self.assertEqual(result["simulation"]["assignment_count"], 1)
        assignment = result["preparation"]["schedule"]["assignments"][0]
        self.assertEqual(assignment["target_location_id"], "loc_greenhouse")

    def test_object_search_uses_region_without_preplacing_target(self) -> None:
        result = self.demo.run("Send one drone east to search for a car.")

        self.assertEqual(result["status"], "simulation_ready")
        target = result["preparation"]["perception_targets"][0]
        self.assertEqual(target["phrase"], "car")
        self.assertFalse(target["known_coordinates"])
        self.assertEqual(target["search_region_id"], "loc_east_field")
        behavior = next(iter(result["simulation"]["task_behaviors"].values()))
        self.assertEqual(behavior["mode"], "search")
        self.assertFalse(behavior["known_target_coordinates"])
        searching = [
            drone
            for snapshot in result["simulation"]["snapshots"]
            for drone in snapshot["drones"]
            if drone["phase"] == "searching"
        ]
        self.assertGreater(len(searching), 2)
        self.assertGreater(
            len({(round(row["latitude"], 7), round(row["longitude"], 7)) for row in searching}),
            2,
        )

    def test_config_exposes_map_and_default_command_without_claiming_completion(self) -> None:
        config = self.demo.config()

        self.assertEqual(len(config["drones"]), 3)
        self.assertGreaterEqual(len(config["map_locations"]), 20)
        self.assertIn("two drones north", config["default_command"].lower())
        self.assertEqual(config["research_status"], "week8_in_progress")


if __name__ == "__main__":
    unittest.main()
