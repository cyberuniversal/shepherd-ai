import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from shepherd_ai.multiuav_checkpoints import RunConfig
from shepherd_ai.multiuav_experiment import EvaluationCase
from shepherd_ai.multiuav_resource_execution import (
    load_bound_resource_config,
    ordered_resource_cases,
    summarize_resource_rows,
)


def _config() -> RunConfig:
    return RunConfig(
        run_id="resource-test",
        study_id="multiuav_validation_placement_v1",
        run_kind="resource",
        model_id="Qwen/Qwen2.5-3B-Instruct",
        model_revision="aa8e72537993ba99e69dfaafa59ed015b17504d1",
        methods=("M1_monolithic",),
        dataset_sha256="a" * 64,
        prompt_contract_version="multiuav_prompt_contract_v1",
        decoding={"do_sample": False, "num_beams": 1, "max_new_tokens": 512},
        code_commit="b" * 40,
        resource_repetition=1,
        hardware_protocol_sha256="c" * 64,
        resource_condition_order=1,
        resource_schedule_sha256="d" * 64,
    )


class MultiUavResourceExecutionTests(unittest.TestCase):
    def test_loads_exact_condition_and_revalidates_hash(self) -> None:
        config = _config()
        artifact = {
            "status": "final_resource_configs_bound_no_measurement_started",
            "code_commit": config.code_commit,
            "configs": [config.to_dict()],
        }

        loaded = load_bound_resource_config(artifact, repetition=1, condition_order=1)

        self.assertEqual(loaded, config)
        artifact["configs"][0]["config_hash"] = "e" * 64
        with self.assertRaisesRegex(ValueError, "hash or payload"):
            load_bound_resource_config(artifact, repetition=1, condition_order=1)

    def test_orders_exactly_150_cases_from_schedule(self) -> None:
        cases = tuple(
            EvaluationCase(f"case-{index:03}", "approved_evaluation_case", {})
            for index in range(150)
        )
        schedule = {
            "case_schedule": {
                "rows": [
                    {
                        "repetition": 1,
                        "case_order": order + 1,
                        "case_id": case.case_id,
                    }
                    for order, case in enumerate(reversed(cases))
                ]
            }
        }

        ordered = ordered_resource_cases(cases, schedule=schedule, repetition=1)

        self.assertEqual(ordered[0].case_id, "case-149")
        self.assertEqual(ordered[-1].case_id, "case-000")

    def test_condition_is_valid_only_when_all_rows_measure_valid(self) -> None:
        config = _config()
        rows = [
            {
                "result_key": f"case-{index}",
                "result": {
                    "resource_measurement": {
                        "valid": True,
                        "run_control": {
                            "protocol_sha256": config.hardware_protocol_sha256,
                            "segment_id": "segment-1",
                            "start_control_sha256": "e" * 64,
                        },
                    }
                },
            }
            for index in range(150)
        ]

        valid = summarize_resource_rows(rows, config=config)
        self.assertTrue(valid["valid"])
        self.assertEqual(valid["segment_count"], 1)
        invalid_rows = copy.deepcopy(rows)
        invalid_rows[10]["result"]["resource_measurement"]["valid"] = False
        invalid = summarize_resource_rows(invalid_rows, config=config)
        self.assertFalse(invalid["valid"])
        self.assertEqual(invalid["invalid_rows_or_controls"], 1)

    def test_validates_start_control_report_hash(self) -> None:
        config = _config()
        report = {
            "schema_version": 1,
            "status": "resource_start_control_passed",
            "protocol_sha256": config.hardware_protocol_sha256,
            "hardware_lock": {"node_name": "node", "gpu_uuid": "GPU-fixed"},
            "warmup": {"complete_method_cases": 1, "output_retained": False},
            "measurement_started": False,
        }
        encoded = json.dumps(
            report, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        )
        report_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        report["sha256"] = report_hash
        rows = [
            {
                "result_key": f"case-{index}",
                "result": {
                    "resource_measurement": {
                        "valid": True,
                        "run_control": {
                            "protocol_sha256": config.hardware_protocol_sha256,
                            "segment_id": "segment-1",
                            "start_control_sha256": report_hash,
                        },
                    }
                },
            }
            for index in range(150)
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "segment-1.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            valid = summarize_resource_rows(
                rows,
                config=config,
                start_control_dir=Path(temporary),
            )
            self.assertTrue(valid["valid"])
            report["warmup"]["output_retained"] = True
            path.write_text(json.dumps(report), encoding="utf-8")
            invalid = summarize_resource_rows(
                rows,
                config=config,
                start_control_dir=Path(temporary),
            )

        self.assertFalse(invalid["valid"])
        self.assertTrue(
            any("report hash differs" in error for error in invalid["errors"])
        )


if __name__ == "__main__":
    unittest.main()
