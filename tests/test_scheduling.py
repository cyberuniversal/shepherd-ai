import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import ground_intent, load_map_locations  # noqa: E402
from shepherd_ai.intent import parse_intent  # noqa: E402
from shepherd_ai.mission_planning import plan_grounded_mission  # noqa: E402
from shepherd_ai.scheduling import (  # noqa: E402
    compare_scheduling_strategies,
    extract_tasks_from_plan_payloads,
    load_drones,
    render_allocation_html,
    render_assignment_csv,
    render_assignment_markdown,
    schedule_tasks,
)


MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
FLEET_PATH = ROOT / "datasets" / "drones" / "week5_three_drone_fleet_v1.json"


def _map_locations() -> dict:
    return {location.id: location for location in load_map_locations(MAP_PATH)}


def _plan_payload(command: str) -> dict:
    locations = load_map_locations(MAP_PATH)
    grounded = ground_intent(parse_intent(command), locations)
    plan = plan_grounded_mission(grounded)
    return {"mission_plan": plan.to_dict()}


class SchedulingTests(unittest.TestCase):
    def test_extract_tasks_replicates_multi_drone_request(self) -> None:
        tasks = extract_tasks_from_plan_payloads([
            _plan_payload("Send two drones north and scan the crops."),
        ])

        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].target_location_id, "loc_north_field")
        self.assertEqual(tasks[0].required_drone_index, 1)
        self.assertEqual(tasks[1].required_drone_index, 2)

    def test_least_loaded_assigns_all_tasks_to_three_simulated_drones(self) -> None:
        locations = _map_locations()
        fleet = json.loads(FLEET_PATH.read_text(encoding="utf-8"))
        drones = load_drones(fleet, locations)
        tasks = extract_tasks_from_plan_payloads(
            [
                _plan_payload("Send two drones north and scan the crops."),
                _plan_payload("Inspect the greenhouse."),
                _plan_payload("Check the irrigation canal."),
            ]
        )

        result = schedule_tasks(tasks, drones, strategy="least_loaded")

        self.assertEqual(result.metrics["assigned_tasks"], 4)
        self.assertEqual(result.metrics["unassigned_tasks"], 0)
        self.assertEqual(result.metrics["drones_used"], 3)
        self.assertEqual(set(result.unassigned_tasks), set())

    def test_unavailable_drone_is_not_assigned(self) -> None:
        locations = _map_locations()
        fleet = json.loads(FLEET_PATH.read_text(encoding="utf-8"))
        fleet["drones"][0]["status"] = "unavailable"
        drones = load_drones(fleet, locations)
        tasks = extract_tasks_from_plan_payloads(
            [
                _plan_payload("Inspect the greenhouse."),
                _plan_payload("Check the irrigation canal."),
            ]
        )

        result = schedule_tasks(tasks, drones, strategy="round_robin")

        assigned_drone_ids = {assignment.drone_id for assignment in result.assignments}
        self.assertNotIn("drone_alpha", assigned_drone_ids)
        self.assertEqual(result.metrics["assigned_tasks"], 2)

    def test_strategy_comparison_reports_metrics_and_best_strategy(self) -> None:
        locations = _map_locations()
        fleet = json.loads(FLEET_PATH.read_text(encoding="utf-8"))
        drones = load_drones(fleet, locations)
        tasks = extract_tasks_from_plan_payloads(
            [
                _plan_payload("Send two drones north and scan the crops."),
                _plan_payload("Inspect the greenhouse."),
                _plan_payload("Check the irrigation canal."),
                _plan_payload("Inspect the storage area."),
            ]
        )

        comparison = compare_scheduling_strategies(tasks, drones)

        self.assertEqual(len(comparison["strategy_results"]), 3)
        self.assertIn(comparison["best_strategy_by_makespan"], {"round_robin", "least_loaded", "nearest_available"})
        for row in comparison["comparison_table"]:
            self.assertEqual(row["unassigned_tasks"], 0)
            self.assertGreater(row["makespan_min"], 0)

    def test_assignment_renderers_include_tables_and_visualization(self) -> None:
        locations = _map_locations()
        fleet = json.loads(FLEET_PATH.read_text(encoding="utf-8"))
        drones = load_drones(fleet, locations)
        tasks = extract_tasks_from_plan_payloads([_plan_payload("Inspect the greenhouse.")])
        result = schedule_tasks(tasks, drones, strategy="least_loaded")

        markdown = render_assignment_markdown(result)
        csv_text = render_assignment_csv(result)
        html = render_allocation_html(result)

        self.assertIn("| Task | Drone |", markdown)
        self.assertIn("task_id,drone_id,strategy", csv_text)
        self.assertIn("<table>", html)
        self.assertIn("Week 5 Drone Allocation", html)


if __name__ == "__main__":
    unittest.main()
