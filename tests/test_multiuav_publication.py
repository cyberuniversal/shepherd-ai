import unittest

from shepherd_ai.multiuav_checkpoints import (
    CHECKPOINT_SCHEMA_VERSION,
    RunConfig,
    result_key,
)
from shepherd_ai.multiuav_prompts import PROMPT_CONTRACT_VERSION
from shepherd_ai.multiuav_publication import validate_accuracy_publication_matrix


def _config(*, run_kind: str = "accuracy") -> RunConfig:
    return RunConfig(
        run_id="locked-accuracy-v1",
        study_id="multiuav_validation_placement_v1",
        run_kind=run_kind,
        model_id="Qwen/Qwen2.5-3B-Instruct",
        model_revision="aa8e72537993ba99e69dfaafa59ed015b17504d1",
        methods=("M1_monolithic", "M3_stage_wise"),
        dataset_sha256="a" * 64,
        prompt_contract_version=PROMPT_CONTRACT_VERSION,
        decoding={"do_sample": False, "num_beams": 1, "max_new_tokens": 512},
        code_commit="b" * 40,
    )


def _row(
    config: RunConfig,
    case_id: str,
    method_id: str,
    *,
    case_status: str = "approved_evaluation_case",
    parse_status: str = "PARSED",
) -> dict:
    return {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "config_hash": config.config_hash,
        "result_key": result_key(case_id, method_id),
        "case_id": case_id,
        "method_id": method_id,
        "model_id": config.model_id,
        "model_revision": config.model_revision,
        "result": {
            "case_id": case_id,
            "case_status": case_status,
            "method_id": method_id,
            "calls": [{"generation": {"raw_output": "{}"}}],
            "final_parse": {"parse_status": parse_status},
            "resource_measurement": None,
        },
    }


class PublicationMatrixTests(unittest.TestCase):
    def _matrix(self, config: RunConfig) -> list[dict]:
        return [
            _row(config, case_id, method_id)
            for case_id in ("case-1", "case-2")
            for method_id in config.methods
        ]

    def test_accepts_complete_accuracy_matrix_and_keeps_parse_errors(self) -> None:
        config = _config()
        rows = self._matrix(config)
        rows[0]["result"]["final_parse"]["parse_status"] = "PARSE_ERROR"

        result = validate_accuracy_publication_matrix(
            config=config,
            rows=rows,
            expected_case_ids=("case-1", "case-2"),
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["rows"], 4)
        self.assertEqual(result["parse_error_rows"], 1)

    def test_rejects_synthetic_fixture_rows(self) -> None:
        config = _config()
        rows = self._matrix(config)
        rows[0]["result"]["case_status"] = "synthetic_unit_fixture"

        with self.assertRaisesRegex(ValueError, "approved evaluation"):
            validate_accuracy_publication_matrix(
                config=config,
                rows=rows,
                expected_case_ids=("case-1", "case-2"),
            )

    def test_rejects_non_accuracy_run_and_incomplete_matrix(self) -> None:
        smoke_config = _config(run_kind="synthetic_smoke")
        with self.assertRaisesRegex(ValueError, "accuracy run"):
            validate_accuracy_publication_matrix(
                config=smoke_config,
                rows=self._matrix(smoke_config),
                expected_case_ids=("case-1", "case-2"),
            )

        config = _config()
        rows = self._matrix(config)
        rows.pop()
        with self.assertRaisesRegex(ValueError, "matrix mismatch"):
            validate_accuracy_publication_matrix(
                config=config,
                rows=rows,
                expected_case_ids=("case-1", "case-2"),
            )

    def test_rejects_resource_measurement_in_accuracy_row(self) -> None:
        config = _config()
        rows = self._matrix(config)
        rows[0]["result"]["resource_measurement"] = {"valid": True}

        with self.assertRaisesRegex(ValueError, "resource measurement"):
            validate_accuracy_publication_matrix(
                config=config,
                rows=rows,
                expected_case_ids=("case-1", "case-2"),
            )


if __name__ == "__main__":
    unittest.main()
