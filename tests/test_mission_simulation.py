import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations
from shepherd_ai.mission_simulation import (
    render_simulation_map,
    schedule_from_payload,
    simulate_schedule,
)
from shepherd_ai.safety import load_safety_policy
from shepherd_ai.scheduling import load_drones
from shepherd_ai.week8_pipeline import prepare_week8_mission


class MissionSimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.locations = load_map_locations(ROOT / "datasets/maps/shepherd_test_map_v1.csv")
        cls.location_index = {location.id: location for location in cls.locations}
        cls.fleet = json.loads(
            (ROOT / "datasets/drones/week5_three_drone_fleet_v1.json").read_text(
                encoding="utf-8"
            )
        )
        cls.policy = load_safety_policy(ROOT / "datasets/safety/week7_safety_policy_v1.json")
        prepared = prepare_week8_mission(
            "Send two drones north to inspect crops and one drone east to inspect irrigation.",
            locations=cls.locations,
            fleet_payload=cls.fleet,
            safety_policy=cls.policy,
            grounding_resolutions={"clause_002": "loc_east_field"},
        )
        cls.schedule = schedule_from_payload(prepared["schedule"])
        cls.drones = load_drones(cls.fleet, cls.location_index)

    def test_three_drone_simulation_completes_with_separation(self) -> None:
        result = simulate_schedule(
            self.schedule,
            self.drones,
            self.locations,
            self.policy,
            time_step_min=0.25,
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["assignment_count"], 3)
        self.assertGreater(len(result["snapshots"]), 10)
        self.assertGreaterEqual(
            result["minimum_observed_separation_m"],
            self.policy.minimum_inter_drone_separation_m,
        )
        self.assertTrue(all(row["phase"] == "completed" for row in result["snapshots"][-1]["drones"]))
        self.assertEqual(result["supervision"]["mission_status"], "completed")
        self.assertEqual(
            sum(event["event_type"] == "task_completed" for event in result["supervision"]["events"]),
            3,
        )
        north_slots = [
            value
            for task_id, value in result["task_slots"].items()
            if value["target_location_id"] == "loc_north_field"
        ]
        self.assertEqual(len(north_slots), 2)
        self.assertNotEqual(
            (north_slots[0]["latitude"], north_slots[0]["longitude"]),
            (north_slots[1]["latitude"], north_slots[1]["longitude"]),
        )

    def test_simulation_map_contains_time_dimension_and_drone_ids(self) -> None:
        result = simulate_schedule(
            self.schedule,
            self.drones,
            self.locations,
            self.policy,
            time_step_min=0.5,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "simulation.html"
            render_simulation_map(result, self.locations, output)
            html = output.read_text(encoding="utf-8")

        self.assertIn("timeDimension", html)
        self.assertIn("drone_alpha", html)
        self.assertIn("drone_bravo", html)
        self.assertIn("drone_charlie", html)

    def test_time_step_must_be_positive(self) -> None:
        with self.assertRaisesRegex(ValueError, "time_step_min must be positive"):
            simulate_schedule(
                self.schedule,
                self.drones,
                self.locations,
                self.policy,
                time_step_min=0.0,
            )


if __name__ == "__main__":
    unittest.main()
