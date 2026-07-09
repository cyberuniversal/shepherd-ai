from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import ground_intent, load_map_locations  # noqa: E402
from shepherd_ai.intent import parse_intent  # noqa: E402
from shepherd_ai.mission_planning import (  # noqa: E402
    MissionPlan,
    MissionPlanStep,
    mission_plan_mermaid,
    mission_plan_networkx_graph,
    mission_plan_task_graph,
    plan_grounded_mission,
    validate_mission_plan,
)


MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"


class MissionPlanningTests(unittest.TestCase):
    def test_plan_grounded_inspection_command_builds_task_sequence(self) -> None:
        grounded = ground_intent(
            parse_intent("Scan the crops in the north field."),
            load_map_locations(MAP_PATH),
        )

        plan = plan_grounded_mission(grounded)
        payload = plan.to_dict()

        self.assertEqual(plan.status, "planned")
        self.assertTrue(plan.ready_for_scheduling)
        self.assertEqual(payload["primary_map_object"]["location_id"], "loc_north_field")
        self.assertEqual(
            [step["action"] for step in payload["steps"]],
            [
                "validate_grounding",
                "takeoff",
                "fly_to",
                "scan_area",
                "capture_images",
                "run_vision_model",
                "save_observation_results",
                "return_to_launch_area",
            ],
        )
        self.assertEqual(payload["steps"][2]["map_object"]["center"]["latitude"], 24.0)
        self.assertEqual(payload["task_graph"]["edges"][0], {"from": "step_001", "to": "step_002"})
        self.assertIn("not scheduling, execution, or safety validation", payload["notes"][0])
        self.assertTrue(validate_mission_plan(plan).valid)

    def test_plan_blocks_ambiguous_grounding(self) -> None:
        grounded = ground_intent(
            parse_intent("Check if there is any traffic on the road."),
            load_map_locations(MAP_PATH),
        )

        plan = plan_grounded_mission(grounded)

        self.assertEqual(plan.status, "blocked")
        self.assertFalse(plan.ready_for_scheduling)
        self.assertIn("grounding_not_ready_for_planning", plan.issues)
        self.assertEqual(plan.steps, ())
        self.assertTrue(validate_mission_plan(plan).valid)

    def test_plan_blocks_missing_map_reference(self) -> None:
        grounded = ground_intent(
            parse_intent("Look for the missing dog."),
            load_map_locations(MAP_PATH),
        )

        plan = plan_grounded_mission(grounded)

        self.assertEqual(plan.status, "blocked")
        self.assertIn("no_grounded_map_reference", plan.issues)
        self.assertIn("grounding_not_ready_for_planning", plan.issues)

    def test_plan_preserves_restricted_area_cautions_without_claiming_safety(self) -> None:
        grounded = ground_intent(
            parse_intent("Check the equipment in the maintenance yard."),
            load_map_locations(MAP_PATH),
        )

        plan = plan_grounded_mission(grounded)

        self.assertEqual(plan.status, "planned")
        self.assertIn("primary_map_object_not_flyable", plan.issues)
        self.assertIn("primary_map_object_requires_clearance", plan.issues)
        self.assertTrue(plan.primary_map_object["requires_clearance"])
        validation = validate_mission_plan(plan)
        self.assertTrue(validation.valid)
        self.assertIn("requires clearance", validation.warnings[1])

    def test_return_command_plans_return_and_landing_steps(self) -> None:
        grounded = ground_intent(
            parse_intent("Return all drones to the launch area."),
            load_map_locations(MAP_PATH),
        )

        plan = plan_grounded_mission(grounded)

        self.assertEqual(plan.status, "planned")
        self.assertEqual(plan.steps[-2].action, "return_to_grounded_location")
        self.assertEqual(plan.steps[-1].action, "land")
        self.assertTrue(validate_mission_plan(plan).valid)

    def test_validation_rejects_forward_dependency(self) -> None:
        plan = MissionPlan(
            status="planned",
            ready_for_scheduling=True,
            intent={"action": "scan"},
            primary_map_object={
                "location_id": "loc_north_field",
                "center": {"latitude": 24.0, "longitude": 46.0},
            },
            referenced_map_objects=(),
            steps=(
                MissionPlanStep(
                    step_id="step_001",
                    action="validate_grounding",
                    description="Validate grounding.",
                    depends_on=("step_999",),
                    map_object={
                        "location_id": "loc_north_field",
                        "center": {"latitude": 24.0, "longitude": 46.0},
                    },
                    expected_output="validated_grounded_map_object",
                ),
            ),
        )

        validation = validate_mission_plan(plan)

        self.assertFalse(validation.valid)
        self.assertIn("first_step_must_not_have_dependencies", validation.issues)
        self.assertIn("step_001_has_unknown_or_forward_dependency_step_999", validation.issues)

    def test_task_graph_lists_nodes_and_edges(self) -> None:
        grounded = ground_intent(
            parse_intent("Scan the crops in the north field."),
            load_map_locations(MAP_PATH),
        )
        graph = mission_plan_task_graph(plan_grounded_mission(grounded))

        self.assertEqual(graph["nodes"][0]["id"], "step_001")
        self.assertEqual(graph["edges"][-1], {"from": "step_007", "to": "step_008"})

    def test_networkx_graph_and_mermaid_flow_are_available(self) -> None:
        grounded = ground_intent(
            parse_intent("Scan the crops in the north field."),
            load_map_locations(MAP_PATH),
        )
        plan = plan_grounded_mission(grounded)
        graph = mission_plan_networkx_graph(plan)
        mermaid = mission_plan_mermaid(plan)

        self.assertEqual(len(graph.nodes), len(plan.steps))
        self.assertIn(("step_006", "step_007"), graph.edges)
        self.assertIn("flowchart TD", mermaid)
        self.assertIn("capture_images", mermaid)
        self.assertIn("run_vision_model", mermaid)

    def test_constraint_bearing_plan_reviews_constraints_before_takeoff(self) -> None:
        grounded = ground_intent(
            parse_intent("Inspect the greenhouse and avoid the power lines."),
            load_map_locations(MAP_PATH),
        )

        plan = plan_grounded_mission(grounded)
        payload = plan.to_dict()

        self.assertEqual(plan.status, "planned")
        self.assertIn("review_constraints", [step.action for step in plan.steps])
        self.assertEqual(plan.steps[1].action, "review_constraints")
        self.assertEqual(plan.steps[2].action, "takeoff")
        self.assertIn("avoid the power lines", plan.steps[1].notes)
        self.assertIn("constraint[0]_not_flyable", plan.issues)
        self.assertIn("constraint[0]_referenced_map_object_not_flyable", plan.issues)
        self.assertEqual(
            {map_object["location_id"] for map_object in payload["referenced_map_objects"]},
            {"loc_greenhouse", "obs_power_lines"},
        )
        self.assertTrue(validate_mission_plan(plan).valid)

    def test_validation_requires_constraint_review_step_when_constraints_exist(self) -> None:
        grounded = ground_intent(
            parse_intent("Scan the crops in the north field."),
            load_map_locations(MAP_PATH),
        )
        base_plan = plan_grounded_mission(grounded)
        plan = MissionPlan(
            status="planned",
            ready_for_scheduling=True,
            intent={"action": "scan", "constraints": ["avoid the power lines"]},
            primary_map_object=base_plan.primary_map_object,
            referenced_map_objects=base_plan.referenced_map_objects,
            steps=base_plan.steps,
        )

        validation = validate_mission_plan(plan)

        self.assertFalse(validation.valid)
        self.assertIn("missing_required_step_action_review_constraints", validation.issues)


if __name__ == "__main__":
    unittest.main()
