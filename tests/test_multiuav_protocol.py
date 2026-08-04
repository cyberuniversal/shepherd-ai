from copy import deepcopy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_protocol import (  # noqa: E402
    build_accuracy_protocol_freeze,
    build_expert_qc_audit,
)


def _cluster(task_id: str, scenario: str, difficulty: str, fact_kind: str) -> dict:
    return {
        "source_task_id": task_id,
        "scenario": scenario,
        "difficulty": difficulty,
        "intervention": {"missing_fact_kind": fact_kind},
        "cases": [{"case_id": f"{task_id}.{index}"} for index in range(5)],
    }


def _pilot_clusters() -> list[dict]:
    clusters = []
    index = 0
    for scenario in ("a", "b", "c"):
        for difficulty in ("easy", "intermediate", "moderate", "hard", "extreme"):
            for fact_kind in ("coverage_threshold", "explicit_drone_identity"):
                index += 1
                clusters.append(
                    _cluster(f"task-{index}", scenario, difficulty, fact_kind)
                )
    return clusters


class MultiUavProtocolTests(unittest.TestCase):
    def test_expert_qc_records_sampled_review_without_claiming_full_review(self) -> None:
        pilot = _pilot_clusters()
        full = deepcopy(pilot)
        full.extend(
            _cluster(f"extra-{index}", "a", "easy", "explicit_drone_identity")
            for index in range(1_443)
        )
        review = {
            "valid": True,
            "summary": {
                "reviewer_ids": ["1"],
                "status_counts": {"approved": 150},
                "cluster_status_counts": {"approved": 30},
            },
        }

        result = build_expert_qc_audit(
            {"clusters": pilot},
            {"clusters": full},
            review,
            reviewer_id="1",
            reviewer_role="mentor",
            reviewer_qualification="PhD",
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["sample"]["cases"], 150)
        self.assertFalse(result["full_row_level_human_review_required"])
        self.assertFalse(result["full_row_level_human_review_performed"])

    def test_expert_qc_rejects_changed_reviewed_cluster(self) -> None:
        pilot = _pilot_clusters()
        full = deepcopy(pilot)
        full[0]["cases"][0]["case_id"] = "changed"
        full.extend(
            _cluster(f"extra-{index}", "a", "easy", "explicit_drone_identity")
            for index in range(1_443)
        )
        review = {
            "valid": True,
            "summary": {
                "reviewer_ids": ["1"],
                "status_counts": {"approved": 150},
                "cluster_status_counts": {"approved": 30},
            },
        }

        with self.assertRaisesRegex(ValueError, "changed in the full draft"):
            build_expert_qc_audit(
                {"clusters": pilot},
                {"clusters": full},
                review,
                reviewer_id="1",
                reviewer_role="mentor",
                reviewer_qualification="PhD",
            )

    def test_accuracy_protocol_freezes_expected_matrix_and_separates_warmup(self) -> None:
        dataset_validation = {
            "valid": True,
            "dataset_sha256": "a" * 64,
            "summary": {
                "split_cluster_counts": {"test": 284},
                "split_case_counts": {"test": 1_420},
            },
        }

        result = build_accuracy_protocol_freeze(
            dataset_validation,
            {"valid": True},
        )

        self.assertEqual(result["expected_accuracy_rows"], 11_360)
        self.assertEqual(result["expected_model_calls"], 17_040)
        self.assertFalse(
            result["run_policy"]["hardware_warmup_required_for_accuracy"]
        )
        self.assertTrue(
            result["run_policy"]["hardware_warmup_required_for_resource_measurement"]
        )
        self.assertFalse(result["study_scores_inspected"])
        self.assertEqual(
            result["scoring_contract_version"],
            "multiuav_accuracy_scoring_v1",
        )
        self.assertTrue(
            result["failure_scoring"][
                "unsafe_proceed_requires_system_released_execute"
            ]
        )


if __name__ == "__main__":
    unittest.main()
