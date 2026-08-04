import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from run_multiuav_accuracy import (  # noqa: E402
    _backend_config,
    _failure_summary,
    _runtime_metadata,
    _validate_runtime_audits,
    load_bound_run_config,
    validate_bound_inputs,
)
from shepherd_ai.multiuav_checkpoints import RunConfig  # noqa: E402
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


def _config() -> RunConfig:
    return RunConfig(
        run_id="accuracy-test",
        study_id="multiuav_validation_placement_v1",
        run_kind="accuracy",
        model_id="Qwen/Qwen2.5-3B-Instruct",
        model_revision="aa8e72537993ba99e69dfaafa59ed015b17504d1",
        methods=(
            "M1_monolithic",
            "M2_post_plan_deterministic",
            "M3_stage_wise",
            "M4_post_plan_compute_matched",
        ),
        dataset_sha256="a" * 64,
        prompt_contract_version="multiuav_prompt_contract_v1",
        decoding={"do_sample": False, "num_beams": 1, "max_new_tokens": 512},
        code_commit="b" * 40,
    )


def _artifact(config: RunConfig) -> dict:
    return {
        "status": "final_accuracy_configs_bound_no_inference_started",
        "code_commit": config.code_commit,
        "expected_rows_per_model": 5_680,
        "expected_rows_total": 11_360,
        "configs": [config.to_dict()],
    }


class RunMultiUavAccuracyTests(unittest.TestCase):
    def test_failure_summary_preserves_stage_and_unscored_status(self) -> None:
        result = _failure_summary(
            {"config_hash": "a" * 64, "study_inference_started": False},
            RuntimeError("load failed"),
            stage="model_load",
            completed_rows=0,
        )

        self.assertEqual(result["status"], "accuracy_run_failed_raw_results_unscored")
        self.assertEqual(result["failure_stage"], "model_load")
        self.assertEqual(result["error_type"], "RuntimeError")
        self.assertEqual(result["error_message"], "load failed")
        self.assertEqual(result["completed_rows"], 0)
        self.assertFalse(result["scores_inspected"])

    def test_runtime_metadata_records_cuda_device(self) -> None:
        class Properties:
            name = "Synthetic GPU"
            total_memory = 4_000

        class Cuda:
            @staticmethod
            def is_available() -> bool:
                return True

            @staticmethod
            def device_count() -> int:
                return 1

            @staticmethod
            def get_device_properties(index: int) -> Properties:
                self.assertEqual(index, 0)
                return Properties()

        class Torch:
            cuda = Cuda()
            version = type("Version", (), {"cuda": "synthetic"})()

        runtime = _runtime_metadata(Torch())

        self.assertTrue(runtime["cuda_available"])
        self.assertEqual(runtime["cuda_runtime"], "synthetic")
        self.assertEqual(runtime["gpus"][0]["name"], "Synthetic GPU")
        self.assertIn("transformers", runtime["package_versions"])

    def test_loads_and_revalidates_bound_config(self) -> None:
        config = _config()

        loaded = load_bound_run_config(_artifact(config), config.model_id)

        self.assertEqual(loaded, config)

    def test_rejects_tampered_config_hash(self) -> None:
        config = _config()
        artifact = _artifact(config)
        artifact["configs"][0]["config_hash"] = "c" * 64

        with self.assertRaisesRegex(ValueError, "hash or payload"):
            load_bound_run_config(artifact, config.model_id)

    def test_validates_manifest_protocol_and_decoding_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.json"
            protocol_path = root / "protocol.json"
            manifest = {"case_count": 1_420}
            protocol = {
                "expected_accuracy_rows": 11_360,
                "decoding": {
                    "do_sample": False,
                    "num_beams": 1,
                    "max_new_tokens": 512,
                },
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
            manifest_hash = sha256_file(manifest_path)
            config = _config()
            config = RunConfig(
                **{
                    **config.payload(),
                    "methods": config.methods,
                    "dataset_sha256": manifest_hash,
                }
            )
            artifact = {
                **_artifact(config),
                "accuracy_manifest_sha256": manifest_hash,
                "protocol_freeze_sha256": sha256_file(protocol_path),
            }

            validate_bound_inputs(
                artifact=artifact,
                config=config,
                manifest_path=manifest_path,
                protocol_path=protocol_path,
                manifest=manifest,
                protocol=protocol,
            )

    def test_runtime_audits_must_match_and_remain_synthetic(self) -> None:
        config = _config()
        cache = {
            "model_id": config.model_id,
            "revision": config.model_revision,
        }
        smoke = {
            "smoke_status": "passed",
            "weights_loaded": True,
            "model_invoked": True,
            "study_cases_evaluated": False,
            "backend_config": {
                "model_id": config.model_id,
                "revision": config.model_revision,
                "do_sample": False,
                "num_beams": 1,
                "dtype": "float16",
                "cache_dir": None,
                "snapshot_dir": None,
                "offload_folder": None,
                "device_map": "auto",
            },
        }

        _validate_runtime_audits(config, cache, smoke)
        backend = _backend_config(config, smoke)

        self.assertEqual(backend.max_new_tokens, 512)
        smoke["study_cases_evaluated"] = True
        with self.assertRaisesRegex(ValueError, "used study cases"):
            _validate_runtime_audits(config, cache, smoke)


if __name__ == "__main__":
    unittest.main()
