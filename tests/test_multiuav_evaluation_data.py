from copy import deepcopy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_evaluation_data import (  # noqa: E402
    APPROVED_CASE_STATUS,
    build_accuracy_case_manifest,
    build_accuracy_run_configs,
    load_accuracy_evaluation_cases,
)
from shepherd_ai.multiuav_interventions import build_draft_cluster  # noqa: E402


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
                "battery": 100,
                "position": {"x": 1, "y": 2, "z": 3},
            }
        ],
        "targets": [],
        "obstacles": [],
        "environment": {},
    }


def _eligibility(task_id: str) -> dict:
    return {
        "task_id": task_id,
        "session_id": "session-1",
        "split": "test",
        "scenario": "target_assignment",
        "difficulty": "easy",
        "eligible": True,
        "selected_alias": "Drone 1 must hover.",
    }


def _full_dataset() -> dict:
    clusters = []
    for index in range(284):
        task_id = f"task-{index:03}"
        task = {"id": task_id, "content": "Drone 1 should hover."}
        clusters.append(build_draft_cluster(_session(), task, _eligibility(task_id)))
    return {
        "metadata": {"data_status": "template_generated_unreviewed_dataset"},
        "clusters": clusters,
    }


def _evidence() -> tuple[dict, dict, dict]:
    return (
        {
            "valid": True,
            "dataset_sha256": "a" * 64,
        },
        {"valid": True},
        {
            "study_scores_inspected": False,
            "dataset": {"dataset_sha256": "a" * 64},
        },
    )


class MultiUavEvaluationDataTests(unittest.TestCase):
    def test_accuracy_manifest_approves_only_complete_test_matrix(self) -> None:
        dataset = _full_dataset()
        validation, qc, protocol = _evidence()

        manifest = build_accuracy_case_manifest(dataset, validation, qc, protocol)

        self.assertEqual(manifest["case_count"], 1_420)
        self.assertEqual(manifest["source_clusters"], 284)
        self.assertTrue(
            all(row["case_status"] == APPROVED_CASE_STATUS for row in manifest["cases"])
        )
        self.assertFalse(
            manifest["human_review_scope"]["full_row_level_human_review_performed"]
        )

    def test_case_loader_materializes_context_without_gold_fields(self) -> None:
        dataset = _full_dataset()
        validation, qc, protocol = _evidence()
        manifest = build_accuracy_case_manifest(dataset, validation, qc, protocol)

        cases = load_accuracy_evaluation_cases(dataset, manifest)

        self.assertEqual(len(cases), 1_420)
        self.assertTrue(all(case.case_status == APPROVED_CASE_STATUS for case in cases))
        self.assertTrue(
            all(
                "registered_decision" not in case.context
                and "proposed_decision" not in case.context
                and "variant" not in case.context
                for case in cases
            )
        )

    def test_case_loader_rejects_approval_metadata_drift(self) -> None:
        dataset = _full_dataset()
        validation, qc, protocol = _evidence()
        manifest = build_accuracy_case_manifest(dataset, validation, qc, protocol)
        corrupted = deepcopy(manifest)
        corrupted["cases"][0]["registered_decision"] = "BLOCK"

        with self.assertRaisesRegex(ValueError, "differs from dataset"):
            load_accuracy_evaluation_cases(dataset, corrupted)

    def test_accuracy_configs_bind_manifest_commit_models_and_methods(self) -> None:
        dataset = _full_dataset()
        validation, qc, protocol_evidence = _evidence()
        manifest = build_accuracy_case_manifest(
            dataset,
            validation,
            qc,
            protocol_evidence,
        )
        protocol = {
            "methods": [
                "M1_monolithic",
                "M2_post_plan_deterministic",
                "M3_stage_wise",
                "M4_post_plan_compute_matched",
            ],
            "decoding": {
                "do_sample": False,
                "num_beams": 1,
                "max_new_tokens": 512,
            },
        }

        configs = build_accuracy_run_configs(
            manifest,
            protocol,
            manifest_sha256="b" * 64,
            code_commit="c" * 40,
        )

        self.assertEqual(len(configs), 2)
        self.assertTrue(all(config.run_kind == "accuracy" for config in configs))
        self.assertTrue(all(config.dataset_sha256 == "b" * 64 for config in configs))
        self.assertTrue(all(config.code_commit == "c" * 40 for config in configs))

    def test_accuracy_configs_reject_unapproved_manifest(self) -> None:
        with self.assertRaisesRegex(ValueError, "approved evaluation data"):
            build_accuracy_run_configs(
                {"data_status": "candidate", "case_count": 1_420},
                {},
                manifest_sha256="b" * 64,
                code_commit="c" * 40,
            )


if __name__ == "__main__":
    unittest.main()
