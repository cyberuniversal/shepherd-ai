import copy
import json
from pathlib import Path
import unittest

from shepherd_ai.multiuav_resource_protocol import (
    build_resource_hardware_protocol,
    finalize_resource_schedule,
)


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "datasets/multiuav_plat"


class MultiUavResourceProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidate = json.loads(
            (METADATA / "resource_schedule_candidate_v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.manifest = json.loads(
            (METADATA / "accuracy_case_manifest_v1.json").read_text(
                encoding="utf-8"
            )
        )

    def test_hardware_protocol_freezes_start_and_failure_controls(self) -> None:
        protocol = build_resource_hardware_protocol()

        self.assertEqual(
            protocol["hardware"]["kubernetes_gpu_product"],
            "NVIDIA-GeForce-RTX-3090",
        )
        self.assertEqual(protocol["backend"]["dtype"], "float16")
        self.assertIsNone(protocol["backend"]["offload_folder"])
        self.assertEqual(
            protocol["start_control"]["post_warmup_consecutive_idle_samples"],
            15,
        )
        self.assertTrue(
            protocol["failure_policy"]["condition_valid_only_if_all_150_rows_valid"]
        )
        self.assertFalse(protocol["measurement_started"])

    def test_final_schedule_contains_only_complete_approved_clusters(self) -> None:
        schedule = self._finalize(self.manifest)

        self.assertEqual(schedule["selection"]["source_task_count"], 30)
        self.assertEqual(schedule["selection"]["case_count"], 150)
        self.assertEqual(schedule["condition_schedule"]["conditions"], 24)
        self.assertEqual(len(schedule["case_schedule"]["rows"]), 450)
        self.assertEqual(schedule["expected"]["total_method_case_rows"], 3_600)
        self.assertFalse(schedule["hidden_fields_in_schedule"])
        for row in schedule["case_schedule"]["rows"]:
            self.assertNotIn("registered_decision", row)
            self.assertNotIn("official_reference", row)

    def test_case_order_is_deterministic_when_manifest_order_changes(self) -> None:
        first = self._finalize(self.manifest)
        reversed_manifest = copy.deepcopy(self.manifest)
        reversed_manifest["cases"].reverse()
        second = self._finalize(reversed_manifest)

        self.assertEqual(first["case_schedule"], second["case_schedule"])

    def test_rejects_missing_selected_case(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        selected = {
            row["task_id"] for row in self.candidate["selection"]["source_tasks"]
        }
        index = next(
            index
            for index, row in enumerate(manifest["cases"])
            if row["source_task_id"] in selected
        )
        del manifest["cases"][index]

        with self.assertRaisesRegex(ValueError, "150 approved cases"):
            self._finalize(manifest)

    def _finalize(self, manifest: dict) -> dict:
        return finalize_resource_schedule(
            candidate=self.candidate,
            accuracy_manifest=manifest,
            candidate_sha256="a" * 64,
            accuracy_manifest_sha256="b" * 64,
            intervention_dataset_sha256="c" * 64,
            hardware_protocol_sha256="d" * 64,
        )


if __name__ == "__main__":
    unittest.main()
