import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import MapLocation, ground_intent, load_map_locations  # noqa: E402
from shepherd_ai.intent import parse_intent  # noqa: E402
from shepherd_ai.mission_planning import plan_grounded_mission  # noqa: E402
from shepherd_ai.safety import (  # noqa: E402
    load_safety_policy,
    validate_inter_drone_separation,
    validate_schedule_safety,
)
from shepherd_ai.scheduling import (  # noqa: E402
    Assignment,
    DroneState,
    ScheduleResult,
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
        self.assertEqual(report.summary["not_evaluated_checks"], 3)

    def test_straight_line_route_crossing_restricted_circle_is_rejected(self) -> None:
        target = MapLocation(
            id="target",
            name="Target",
            category="field",
            latitude=24.0,
            longitude=46.002,
            radius_m=20.0,
        )
        obstacle = MapLocation(
            id="restricted",
            name="Restricted",
            category="restricted_area",
            latitude=24.0,
            longitude=46.001,
            radius_m=30.0,
            map_role="restricted_area",
            flyable=False,
            requires_clearance=True,
        )
        schedule = ScheduleResult(
            strategy="least_loaded",
            assignments=(
                Assignment(
                    task_id="task_1",
                    drone_id="drone_1",
                    strategy="least_loaded",
                    start_min=0.0,
                    end_min=1.0,
                    duration_min=1.0,
                    travel_distance_m=200.0,
                    target_location_id="target",
                    target_name="Target",
                    action="inspect",
                ),
            ),
            unassigned_tasks=(),
            metrics={},
        )
        drone = DroneState(
            drone_id="drone_1",
            status="idle",
            current_location_id="start",
            current_latitude=24.0,
            current_longitude=46.0,
            available_at_min=0.0,
            battery_percent=90.0,
            speed_m_per_min=300.0,
        )

        report = validate_schedule_safety(
            schedule,
            (drone,),
            {"target": target, "restricted": obstacle},
            load_safety_policy(POLICY_PATH),
            mission_altitude_m=30.0,
        )

        restricted = next(
            check
            for check in report.assignment_results[0].checks
            if check.category == "restricted_area"
        )
        self.assertEqual(report.status, "rejected")
        self.assertEqual(restricted.reason, "straight_line_route_intersects_restricted_area")
        self.assertEqual(restricted.evidence["route_intersections"][0]["location_id"], "restricted")

    def test_inter_drone_separation_rejects_pair_below_threshold(self) -> None:
        first = DroneState(
            drone_id="drone_1",
            status="idle",
            current_location_id="one",
            current_latitude=24.0,
            current_longitude=46.0,
            available_at_min=0.0,
            battery_percent=90.0,
            speed_m_per_min=300.0,
        )
        second = DroneState(
            drone_id="drone_2",
            status="idle",
            current_location_id="two",
            current_latitude=24.0,
            current_longitude=46.00001,
            available_at_min=0.0,
            battery_percent=90.0,
            speed_m_per_min=300.0,
        )

        check = validate_inter_drone_separation(
            (first, second),
            load_safety_policy(POLICY_PATH),
        )

        self.assertEqual(check.status, "failed")
        self.assertEqual(check.category, "inter_drone_separation")
        self.assertEqual(check.evidence["violating_pairs"][0]["drone_ids"], ["drone_1", "drone_2"])


if __name__ == "__main__":
    unittest.main()
