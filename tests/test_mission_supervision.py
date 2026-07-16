import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import ground_intent, load_map_locations  # noqa: E402
from shepherd_ai.intent import parse_intent  # noqa: E402
from shepherd_ai.mission_planning import plan_grounded_mission  # noqa: E402
from shepherd_ai.mission_supervision import MissionSupervisor  # noqa: E402
from shepherd_ai.safety import load_safety_policy  # noqa: E402
from shepherd_ai.scheduling import (  # noqa: E402
    extract_tasks_from_plan_payloads,
    load_drones,
    schedule_tasks,
)


MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
FLEET_PATH = ROOT / "datasets" / "drones" / "week5_three_drone_fleet_v1.json"
POLICY_PATH = ROOT / "datasets" / "safety" / "week7_safety_policy_v1.json"


def _supervisor(command: str = "Inspect the greenhouse.") -> tuple[MissionSupervisor, tuple]:
    locations = load_map_locations(MAP_PATH)
    location_index = {location.id: location for location in locations}
    fleet = json.loads(FLEET_PATH.read_text(encoding="utf-8"))
    drones = load_drones(fleet, location_index)
    grounded = ground_intent(parse_intent(command), locations)
    plan = plan_grounded_mission(grounded)
    tasks = extract_tasks_from_plan_payloads([{"mission_plan": plan.to_dict()}])
    schedule = schedule_tasks(tasks, drones, strategy="least_loaded")
    return (
        MissionSupervisor(
            schedule,
            drones,
            location_index,
            load_safety_policy(POLICY_PATH),
            mission_altitude_m=30.0,
        ),
        drones,
    )


class MissionSupervisorTests(unittest.TestCase):
    def test_confirmation_and_completion_are_real_state_transitions(self) -> None:
        supervisor, drones = _supervisor()

        self.assertEqual(supervisor.snapshot()["mission_status"], "awaiting_confirmation")
        supervisor.confirm_and_start(drones)
        task_id = next(iter(supervisor.snapshot()["tasks"]))
        supervisor.complete_task(task_id)

        snapshot = supervisor.snapshot()
        self.assertEqual(snapshot["mission_status"], "completed")
        self.assertEqual(snapshot["tasks"][task_id]["status"], "completed")
        self.assertEqual(
            [event["event_type"] for event in snapshot["events"]],
            ["mission_created", "operator_confirmed", "task_completed"],
        )
        self.assertTrue(all(event["mode"] == "event_driven_simulation" for event in snapshot["events"]))

    def test_low_battery_telemetry_requests_return_instead_of_continuing(self) -> None:
        supervisor, drones = _supervisor()
        supervisor.confirm_and_start(drones)
        assigned_id = next(iter(supervisor.snapshot()["tasks"].values()))["drone_id"]
        low_battery = tuple(
            type(drone)(**{**drone.to_dict(), "battery_percent": 10.0})
            if drone.drone_id == assigned_id
            else drone
            for drone in drones
        )

        supervisor.apply_telemetry(low_battery)

        snapshot = supervisor.snapshot()
        task = next(iter(snapshot["tasks"].values()))
        self.assertEqual(snapshot["mission_status"], "intervention_required")
        self.assertEqual(task["status"], "return_requested")
        self.assertEqual(snapshot["events"][-1]["intervention"], "return_to_launch_requested")
        self.assertIn("battery", snapshot["events"][-1]["failed_categories"])

    def test_unavailable_drone_pauses_and_requests_replanning(self) -> None:
        supervisor, drones = _supervisor()
        supervisor.confirm_and_start(drones)
        assigned_id = next(iter(supervisor.snapshot()["tasks"].values()))["drone_id"]
        unavailable = tuple(
            type(drone)(**{**drone.to_dict(), "status": "unavailable"})
            if drone.drone_id == assigned_id
            else drone
            for drone in drones
        )

        supervisor.apply_telemetry(unavailable)

        snapshot = supervisor.snapshot()
        task = next(iter(snapshot["tasks"].values()))
        self.assertEqual(snapshot["mission_status"], "paused")
        self.assertEqual(task["status"], "paused")
        self.assertEqual(snapshot["events"][-1]["intervention"], "hold_and_replan_requested")

    def test_separation_violation_pauses_multi_drone_mission(self) -> None:
        supervisor, drones = _supervisor("Send two drones north and scan the crops.")
        supervisor.confirm_and_start(drones)
        assigned_ids = {task["drone_id"] for task in supervisor.snapshot()["tasks"].values()}
        converged = tuple(
            type(drone)(
                **{
                    **drone.to_dict(),
                    "current_latitude": 24.0,
                    "current_longitude": 46.0,
                }
            )
            if drone.drone_id in assigned_ids
            else drone
            for drone in drones
        )

        supervisor.apply_telemetry(converged)

        snapshot = supervisor.snapshot()
        self.assertEqual(snapshot["mission_status"], "paused")
        self.assertEqual(snapshot["events"][-1]["intervention"], "hold_and_replan_requested")
        self.assertIn("inter_drone_separation", snapshot["events"][-1]["failed_categories"])

    def test_operator_can_pause_resume_and_cancel(self) -> None:
        supervisor, drones = _supervisor()
        supervisor.confirm_and_start(drones)

        supervisor.pause("operator_review")
        self.assertEqual(supervisor.snapshot()["mission_status"], "paused")
        supervisor.resume(drones)
        self.assertEqual(supervisor.snapshot()["mission_status"], "active")
        supervisor.cancel("operator_cancelled")

        snapshot = supervisor.snapshot()
        self.assertEqual(snapshot["mission_status"], "cancelled")
        self.assertTrue(all(task["status"] == "cancelled" for task in snapshot["tasks"].values()))
        self.assertEqual(
            [event["event_type"] for event in snapshot["events"]][-3:],
            ["operator_paused", "operator_resumed", "operator_cancelled"],
        )

    def test_failed_preflight_never_enters_active_state(self) -> None:
        supervisor, drones = _supervisor("Check the equipment in the maintenance yard.")

        supervisor.confirm_and_start(drones)

        snapshot = supervisor.snapshot()
        self.assertEqual(snapshot["mission_status"], "blocked")
        self.assertTrue(all(task["status"] == "blocked" for task in snapshot["tasks"].values()))
        self.assertEqual(snapshot["events"][-1]["event_type"], "preflight_blocked")


if __name__ == "__main__":
    unittest.main()
