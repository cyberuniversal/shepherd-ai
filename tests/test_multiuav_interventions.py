from pathlib import Path
from copy import deepcopy
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_interventions import (  # noqa: E402
    apply_context_patch,
    build_draft_cluster,
    compact_review_row,
    materialize_case_context,
    select_stratified_training_pilot,
    validate_draft_cluster,
    validate_unreviewed_pilot_dataset,
)


def _session() -> dict:
    return {
        "id": "session-1",
        "task_type": "target_assignment",
        "canvas_width": 1000,
        "canvas_height": 800,
        "is_distance_3d": True,
        "status": "active",
        "drones": [
            {
                "id": "drone-id-1",
                "name": "Drone 1",
                "status": "idle",
                "position": {"x": 0, "y": 0, "z": 0},
            },
            {
                "id": "drone-id-2",
                "name": "Drone 2",
                "status": "idle",
                "position": {"x": 1, "y": 1, "z": 0},
            },
        ],
        "environment": {"id": "env-1", "name": "Clear", "weather": "clear"},
    }


def _eligibility(task_id: str = "task-1") -> dict:
    return {
        "task_id": task_id,
        "session_id": "session-1",
        "split": "train",
        "scenario": "target_assignment",
        "difficulty": "easy",
        "eligible": True,
        "selected_alias": "Have Drone 1 take off and hover.",
    }


class MultiUavInterventionTests(unittest.TestCase):
    def test_identity_cluster_is_complete_distinct_and_unreviewed(self) -> None:
        task = {
            "id": "task-1",
            "content": "Command drone Drone 1 to take off to 12 meters and hover.",
        }
        cluster = build_draft_cluster(_session(), task, _eligibility())
        cases = {case["variant"]: case for case in cluster["cases"]}

        self.assertEqual(len(cases), 5)
        self.assertEqual(
            cases["missing_information_clarify"]["instruction"],
            "Command assigned UAV A to take off to 12 meters and hover.",
        )
        self.assertEqual(
            cases["restored_information_execute"]["instruction"],
            "Command assigned UAV A (Drone 1) to take off to 12 meters and hover.",
        )
        self.assertNotIn(
            "drone the",
            cases["missing_information_clarify"]["instruction"].lower(),
        )
        self.assertTrue(
            all(
                case["label_status"] == "pending_human_review"
                for case in cases.values()
            )
        )
        conflict = apply_context_patch(
            cluster["context"]["payload"],
            cases["resource_conflict_block"]["context_patch"],
        )
        self.assertEqual([drone["name"] for drone in conflict["drones"]], ["Drone 2"])
        missing_context = materialize_case_context(
            cluster,
            cases["missing_information_clarify"],
        )
        self.assertEqual(
            missing_context["instruction"],
            cases["missing_information_clarify"]["instruction"],
        )
        self.assertNotIn("Drone 1", missing_context["instruction"])

    def test_generic_coverage_cluster_uses_threshold_control(self) -> None:
        task = {
            "id": "task-2",
            "content": "Take off necessary drones until session progress exceeds 95%.",
        }
        eligibility = _eligibility("task-2")
        eligibility["selected_alias"] = (
            "Use available drones until progress is over 95%."
        )
        cluster = build_draft_cluster(_session(), task, eligibility)
        cases = {case["variant"]: case for case in cluster["cases"]}

        self.assertEqual(
            cases["missing_information_clarify"]["instruction"],
            "Take off necessary drones until session progress "
            "exceeds the required threshold.",
        )
        self.assertEqual(
            cases["restored_information_execute"]["instruction"],
            "Take off necessary drones until session progress "
            "exceeds the required threshold (95%).",
        )
        conflict = apply_context_patch(
            cluster["context"]["payload"],
            cases["resource_conflict_block"]["context_patch"],
        )
        self.assertEqual(conflict["drones"], [])

    def test_plural_drone_prefix_and_source_whitespace_are_handled(self) -> None:
        task = {
            "id": "task-1",
            "content": "Drones Drone 1 and Drone 2  should hover.",
        }
        cluster = build_draft_cluster(_session(), task, _eligibility())
        cases = {case["variant"]: case for case in cluster["cases"]}

        self.assertEqual(
            cases["canonical_execute"]["instruction"],
            "Drones Drone 1 and Drone 2  should hover.",
        )
        self.assertEqual(
            cases["missing_information_clarify"]["instruction"],
            "Assigned UAV A and Assigned UAV B should hover.",
        )

    def test_partial_cluster_is_rejected(self) -> None:
        task = {"id": "task-1", "content": "Drone 1 should hover."}
        cluster = build_draft_cluster(_session(), task, _eligibility())
        cluster["cases"].pop()

        with self.assertRaisesRegex(ValueError, "exactly five"):
            validate_draft_cluster(cluster)

    def test_privileged_field_in_cluster_is_rejected(self) -> None:
        task = {"id": "task-1", "content": "Drone 1 should hover."}
        cluster = build_draft_cluster(_session(), task, _eligibility())
        cluster["annotation"] = {"execution_check_apis": {"hidden": True}}

        with self.assertRaisesRegex(ValueError, "privileged fields"):
            validate_draft_cluster(cluster)

    def test_pilot_selection_is_training_only_and_stratified(self) -> None:
        rows = []
        for scenario in ("area_search", "target_assignment"):
            for difficulty in ("easy", "hard"):
                for index in range(3):
                    rows.append(
                        {
                            "task_id": f"{scenario}-{difficulty}-{index}",
                            "scenario": scenario,
                            "difficulty": difficulty,
                            "split": "train",
                            "eligible": True,
                        }
                    )
        rows.append(
            {
                "task_id": "test-leak",
                "scenario": "area_search",
                "difficulty": "easy",
                "split": "test",
                "eligible": True,
            }
        )

        selected = select_stratified_training_pilot(rows, per_stratum=2)

        self.assertEqual(len(selected), 8)
        self.assertTrue(all(row["split"] == "train" for row in selected))

    def test_pilot_validator_rejects_review_packet_mutation(self) -> None:
        scenarios = (
            "area_assignment_and_patrol",
            "area_search",
            "target_assignment",
        )
        difficulties = ("easy", "moderate", "intermediate", "hard", "extreme")
        eligibility_rows = []
        source_by_id = {}
        clusters = []
        for scenario in scenarios:
            for difficulty in difficulties:
                task_id = f"{scenario}-{difficulty}"
                eligibility = _eligibility(task_id)
                eligibility["scenario"] = scenario
                eligibility["difficulty"] = difficulty
                eligibility_rows.append(eligibility)
                task = {"id": task_id, "content": "Drone 1 should hover."}
                source_by_id[task_id] = {"session": _session(), "task": task}
                clusters.append(build_draft_cluster(_session(), task, eligibility))
        dataset = {
            "metadata": {
                "split": "train",
                "data_status": "template_generated_unreviewed_pilot",
                "selection_seed": "test-seed",
            },
            "clusters": clusters,
        }
        review_rows = [
            compact_review_row(cluster)
            for cluster in clusters
        ]
        validate_unreviewed_pilot_dataset(
            dataset,
            review_rows,
            eligibility_rows,
            source_by_id,
            expected_per_stratum=1,
        )

        corrupted = deepcopy(review_rows)
        corrupted[0]["reviewer_id"] = "fabricated-reviewer"
        with self.assertRaisesRegex(ValueError, "review row differs"):
            validate_unreviewed_pilot_dataset(
                dataset,
                corrupted,
                eligibility_rows,
                source_by_id,
                expected_per_stratum=1,
            )


if __name__ == "__main__":
    unittest.main()
