from pathlib import Path
from copy import deepcopy
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_interventions import (  # noqa: E402
    apply_context_patch,
    build_draft_cluster,
    compact_review_rows,
    materialize_case_context,
    normalize_accepted_review_rows,
    prepare_pilot_review_rows,
    run_validator_negative_controls,
    select_stratified_training_pilot,
    validate_completed_pilot_review,
    validate_draft_cluster,
    validate_unreviewed_intervention_dataset,
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

    def test_balanced_pilot_selects_each_supported_fact_kind_per_stratum(self) -> None:
        rows = []
        kinds = {}
        for scenario in ("area_search", "target_assignment"):
            for difficulty in ("easy", "hard"):
                for kind in ("explicit_drone_identity", "coverage_threshold"):
                    task_id = f"{scenario}-{difficulty}-{kind}"
                    rows.append(
                        {
                            "task_id": task_id,
                            "scenario": scenario,
                            "difficulty": difficulty,
                            "split": "train",
                            "eligible": True,
                        }
                    )
                    kinds[task_id] = kind

        selected = select_stratified_training_pilot(
            rows,
            per_stratum=2,
            fact_kind_by_task_id=kinds,
        )

        for scenario in ("area_search", "target_assignment"):
            for difficulty in ("easy", "hard"):
                selected_kinds = {
                    kinds[row["task_id"]]
                    for row in selected
                    if row["scenario"] == scenario
                    and row["difficulty"] == difficulty
                }
                self.assertEqual(
                    selected_kinds,
                    {"explicit_drone_identity", "coverage_threshold"},
                )

    def test_compact_review_has_one_instruction_and_task_specific_conflict(self) -> None:
        task = {"id": "task-1", "content": "Drone 1 should hover at (2, 3, 4)."}
        cluster = build_draft_cluster(_session(), task, _eligibility())

        rows = compact_review_rows(cluster)

        self.assertEqual(len(rows), 5)
        self.assertTrue(all("instruction" in row for row in rows))
        self.assertTrue(all("canonical_instruction" not in row for row in rows))
        conflict = next(
            row for row in rows if row["variant"] == "resource_conflict_block"
        )
        self.assertIn("Drone 1", conflict["intervention_summary"])
        self.assertIn("base fleet=2", conflict["uav_status_summary"])
        self.assertIn("case fleet=1", conflict["uav_status_summary"])

    def test_validator_rejects_ineffective_resource_conflict_patch(self) -> None:
        task = {"id": "task-1", "content": "Drone 1 should hover."}
        cluster = build_draft_cluster(_session(), task, _eligibility())
        conflict = next(
            case
            for case in cluster["cases"]
            if case["variant"] == "resource_conflict_block"
        )
        conflict["context_patch"]["drone_references"] = ["Drone 999"]

        with self.assertRaisesRegex(ValueError, "differs from required UAVs"):
            validate_draft_cluster(cluster)

    def test_cluster_remains_valid_after_json_round_trip(self) -> None:
        task = {"id": "task-1", "content": "Drone 1 should hover."}
        cluster = build_draft_cluster(_session(), task, _eligibility())

        validate_draft_cluster(json.loads(json.dumps(cluster)))

    def test_negative_control_audit_observes_two_rejections(self) -> None:
        identity = build_draft_cluster(
            _session(),
            {"id": "task-1", "content": "Drone 1 should hover."},
            _eligibility(),
        )

        results = run_validator_negative_controls({"clusters": [identity]})

        self.assertEqual(len(results), 2)
        self.assertTrue(all(row["observed"] == "rejected" for row in results))
        self.assertTrue(
            all(
                row["data_status"]
                == "synthetic_negative_control_not_study_data"
                for row in results
            )
        )

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
            row for cluster in clusters for row in compact_review_rows(cluster)
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

    def test_full_dataset_validator_reconstructs_every_eligible_task(self) -> None:
        train = _eligibility("task-train")
        test = _eligibility("task-test")
        test["split"] = "test"
        eligibility_rows = [train, test, {**_eligibility("excluded"), "eligible": False}]
        source_by_id = {
            "task-train": {
                "session": _session(),
                "task": {"id": "task-train", "content": "Drone 1 should hover."},
            },
            "task-test": {
                "session": _session(),
                "task": {"id": "task-test", "content": "Drone 2 should hover."},
            },
        }
        clusters = [
            build_draft_cluster(
                source_by_id[row["task_id"]]["session"],
                source_by_id[row["task_id"]]["task"],
                row,
            )
            for row in (train, test)
        ]
        review_rows = [
            row for cluster in clusters for row in compact_review_rows(cluster)
        ]
        dataset = {
            "metadata": {
                "data_status": "template_generated_unreviewed_dataset",
            },
            "clusters": clusters,
        }

        result = validate_unreviewed_intervention_dataset(
            dataset,
            review_rows,
            eligibility_rows,
            source_by_id,
        )

        self.assertEqual(result["eligible_clusters"], 2)
        self.assertEqual(result["excluded_source_tasks"], 1)
        self.assertEqual(result["cases"], 10)
        self.assertEqual(result["split_cluster_counts"], {"test": 1, "train": 1})

    def test_full_dataset_validator_rejects_missing_eligible_cluster(self) -> None:
        eligibility = _eligibility("task-1")
        source = {
            "task-1": {
                "session": _session(),
                "task": {"id": "task-1", "content": "Drone 1 should hover."},
            }
        }
        dataset = {
            "metadata": {
                "data_status": "template_generated_unreviewed_dataset",
            },
            "clusters": [],
        }

        with self.assertRaisesRegex(ValueError, "cover every eligible task"):
            validate_unreviewed_intervention_dataset(
                dataset,
                [],
                [eligibility],
                source,
            )

    def test_completed_review_accepts_explicit_approved_judgments(self) -> None:
        task = {"id": "task-1", "content": "Drone 1 should hover."}
        cluster = build_draft_cluster(_session(), task, _eligibility())
        dataset = {"clusters": [cluster]}
        rows = prepare_pilot_review_rows(
            compact_review_rows(cluster),
            "reviewer_alpha",
        )
        for row in rows:
            row["review_status"] = "approved"
            row["case_valid"] = "yes"

        result = validate_completed_pilot_review(dataset, rows)

        self.assertTrue(result["valid"])
        self.assertEqual(result["status_counts"], {"approved": 5})
        self.assertEqual(result["cluster_status_counts"], {"approved": 1})
        self.assertEqual(result["reviewer_ids"], ["reviewer_alpha"])

    def test_accept_notes_can_be_normalized_with_numeric_reviewer_id(self) -> None:
        task = {"id": "task-1", "content": "Drone 1 should hover."}
        cluster = build_draft_cluster(_session(), task, _eligibility())
        rows = compact_review_rows(cluster)
        for row in rows:
            row["reviewer_notes"] = "Accept: case is valid."

        normalized = normalize_accepted_review_rows(rows, "1")
        result = validate_completed_pilot_review(
            {"clusters": [cluster]},
            normalized,
        )

        self.assertTrue(all(row["reviewer_id"] == "1" for row in normalized))
        self.assertTrue(all(row["review_status"] == "approved" for row in normalized))
        self.assertTrue(all(row["case_valid"] == "yes" for row in normalized))
        self.assertEqual(result["reviewer_ids"], ["1"])

    def test_accept_note_normalization_rejects_missing_or_existing_judgments(self) -> None:
        task = {"id": "task-1", "content": "Drone 1 should hover."}
        cluster = build_draft_cluster(_session(), task, _eligibility())
        rows = compact_review_rows(cluster)
        for row in rows:
            row["reviewer_notes"] = "Accept: case is valid."
        rows[0]["reviewer_notes"] = "Needs revision: ambiguous target."

        with self.assertRaisesRegex(ValueError, "must begin with 'Accept:'"):
            normalize_accepted_review_rows(rows, "1")

        rows[0]["reviewer_notes"] = "Accept: case is valid."
        rows[0]["review_status"] = "excluded"
        with self.assertRaisesRegex(ValueError, "already populated"):
            normalize_accepted_review_rows(rows, "1")

    def test_completed_review_rejects_mutation_and_incomplete_judgment(self) -> None:
        task = {"id": "task-1", "content": "Drone 1 should hover."}
        cluster = build_draft_cluster(_session(), task, _eligibility())
        dataset = {"clusters": [cluster]}
        rows = prepare_pilot_review_rows(
            compact_review_rows(cluster),
            "reviewer_alpha",
        )
        rows[0]["review_status"] = "approved"
        rows[0]["case_valid"] = "yes"

        with self.assertRaisesRegex(ValueError, "must be yes or no"):
            validate_completed_pilot_review(dataset, rows)

        rows[0]["instruction"] = "Changed source instruction"
        with self.assertRaisesRegex(ValueError, "immutable review field changed"):
            validate_completed_pilot_review(dataset, rows)

    def test_completed_review_records_revision_without_approving_it(self) -> None:
        task = {"id": "task-1", "content": "Drone 1 should hover."}
        cluster = build_draft_cluster(_session(), task, _eligibility())
        dataset = {"clusters": [cluster]}
        rows = prepare_pilot_review_rows(
            compact_review_rows(cluster),
            "reviewer_alpha",
        )
        for row in rows:
            row.update({"review_status": "approved", "case_valid": "yes"})
        rows[0].update(
            {
                "review_status": "needs_revision",
                "case_valid": "no",
                "reviewer_notes": "The missing fact is still recoverable.",
            }
        )

        result = validate_completed_pilot_review(dataset, rows)

        self.assertEqual(
            result["status_counts"],
            {"approved": 4, "needs_revision": 1},
        )
        self.assertEqual(
            result["cluster_status_counts"],
            {"needs_revision": 1},
        )


if __name__ == "__main__":
    unittest.main()
