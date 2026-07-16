import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import ground_intent, load_map_locations  # noqa: E402
from shepherd_ai.intent import parse_intent  # noqa: E402
from shepherd_ai.mission_planning import plan_grounded_mission  # noqa: E402
from shepherd_ai.safety import load_safety_policy, validate_schedule_safety  # noqa: E402
from shepherd_ai.scheduling import (  # noqa: E402
    DroneState,
    extract_tasks_from_plan_payloads,
    load_drones,
    schedule_tasks,
)


MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
FLEET_PATH = ROOT / "datasets" / "drones" / "week5_three_drone_fleet_v1.json"
POLICY_PATH = ROOT / "datasets" / "safety" / "week7_safety_policy_v1.json"


def _locations() -> dict:
    return {location.id: location for location in load_map_locations(MAP_PATH)}


def _schedule(command: str):
    locations = _locations()
    fleet = json.loads(FLEET_PATH.read_text(encoding="utf-8"))
    drones = load_drones(fleet, locations)
    grounded = ground_intent(parse_intent(command), locations.values())
    plan = plan_grounded_mission(grounded)
    tasks = extract_tasks_from_plan_payloads([{"mission_plan": plan.to_dict()}])
    return schedule_tasks(tasks, drones, strategy="least_loaded"), drones, locations


class SafetyTests(unittest.TestCase):
    def test_policy_rejects_default_altitude_above_maximum(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["default_mission_altitude_m"] = payload["maximum_altitude_m"] + 1

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid_policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "default_mission_altitude_m"):
                load_safety_policy(path)

    def test_safe_assignment_passes_all_four_roadmap_checks(self) -> None:
        schedule, drones, locations = _schedule("Inspect the greenhouse.")
        policy = load_safety_policy(POLICY_PATH)

        report = validate_schedule_safety(
            schedule,
            drones,
            locations,
            policy,
            mission_altitude_m=30.0,
        )

        self.assertEqual(report.status, "approved")
        self.assertTrue(report.safe_to_execute)
        self.assertEqual(report.summary["passed_checks"], 4)
        self.assertEqual(
            {check.category for check in report.assignment_results[0].checks},
            {"availability", "battery", "altitude", "restricted_area"},
        )

    def test_low_battery_rejects_assigned_drone(self) -> None:
        schedule, drones, locations = _schedule("Inspect the greenhouse.")
        assigned_id = schedule.assignments[0].drone_id
        current_drones = tuple(
            DroneState(**{**drone.to_dict(), "battery_percent": 10.0})
            if drone.drone_id == assigned_id
            else drone
            for drone in drones
        )

        report = validate_schedule_safety(
            schedule,
            current_drones,
            locations,
            load_safety_policy(POLICY_PATH),
            mission_altitude_m=30.0,
        )

        self.assertEqual(report.status, "rejected")
        battery = next(
            check for check in report.assignment_results[0].checks if check.category == "battery"
        )
        self.assertEqual(battery.status, "failed")
        self.assertEqual(battery.evidence["battery_percent"], 10.0)

    def test_restricted_primary_target_is_rejected(self) -> None:
        schedule, drones, locations = _schedule("Check the equipment in the maintenance yard.")

        report = validate_schedule_safety(
            schedule,
            drones,
            locations,
            load_safety_policy(POLICY_PATH),
            mission_altitude_m=30.0,
        )

        restricted = next(
            check
            for check in report.assignment_results[0].checks
            if check.category == "restricted_area"
        )
        self.assertEqual(report.status, "rejected")
        self.assertEqual(restricted.status, "failed")
        self.assertEqual(restricted.evidence["map_role"], "restricted_area")

    def test_altitude_above_policy_limit_is_rejected(self) -> None:
        schedule, drones, locations = _schedule("Inspect the greenhouse.")

        report = validate_schedule_safety(
            schedule,
            drones,
            locations,
            load_safety_policy(POLICY_PATH),
            mission_altitude_m=61.0,
        )

        altitude = next(
            check for check in report.assignment_results[0].checks if check.category == "altitude"
        )
        self.assertEqual(report.status, "rejected")
        self.assertEqual(altitude.status, "failed")
        self.assertEqual(altitude.evidence["maximum_altitude_m"], 60.0)

    def test_post_schedule_availability_change_is_rejected(self) -> None:
        schedule, drones, locations = _schedule("Inspect the greenhouse.")
        assigned_id = schedule.assignments[0].drone_id
        current_drones = tuple(
            DroneState(**{**drone.to_dict(), "status": "unavailable"})
            if drone.drone_id == assigned_id
            else drone
            for drone in drones
        )

        report = validate_schedule_safety(
            schedule,
            current_drones,
            locations,
            load_safety_policy(POLICY_PATH),
            mission_altitude_m=30.0,
        )

        availability = next(
            check
            for check in report.assignment_results[0].checks
            if check.category == "availability"
        )
        self.assertEqual(report.status, "rejected")
        self.assertEqual(availability.status, "failed")
        self.assertEqual(availability.evidence["drone_status"], "unavailable")

    def test_missing_assigned_drone_state_makes_report_incomplete(self) -> None:
        schedule, drones, locations = _schedule("Inspect the greenhouse.")
        assigned_id = schedule.assignments[0].drone_id

        report = validate_schedule_safety(
            schedule,
            tuple(drone for drone in drones if drone.drone_id != assigned_id),
            locations,
            load_safety_policy(POLICY_PATH),
            mission_altitude_m=30.0,
        )

        self.assertEqual(report.status, "incomplete")
        self.assertFalse(report.safe_to_execute)
        self.assertEqual(report.summary["not_evaluated_checks"], 2)


if __name__ == "__main__":
    unittest.main()
