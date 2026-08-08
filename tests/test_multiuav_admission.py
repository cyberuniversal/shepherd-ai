import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from shepherd_ai.multiuav_admission import (
    admit_accuracy_checkpoint,
    admit_accuracy_study,
)
from shepherd_ai.multiuav_checkpoints import (
    CHECKPOINT_SCHEMA_VERSION,
    RunConfig,
    result_key,
)


def _config(model_id: str = "Qwen/Qwen2.5-3B-Instruct") -> RunConfig:
    revisions = {
        "Qwen/Qwen2.5-3B-Instruct": (
            "aa8e72537993ba99e69dfaafa59ed015b17504d1"
        ),
        "Qwen/Qwen2.5-7B-Instruct": (
            "a09a35458c702b33eeacc393d103063234e8bc28"
        ),
    }
    return RunConfig(
        run_id=f"accuracy-{model_id}",
        study_id="multiuav_validation_placement_v1",
        run_kind="accuracy",
        model_id=model_id,
        model_revision=revisions[model_id],
        methods=("M1_monolithic", "M3_stage_wise"),
        dataset_sha256="a" * 64,
        prompt_contract_version="multiuav_prompt_contract_v1",
        decoding={"do_sample": False, "num_beams": 1, "max_new_tokens": 512},
        code_commit="b" * 40,
    )


def _row(config: RunConfig, case_id: str, method_id: str) -> dict:
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
            "case_status": "approved_evaluation_case",
            "method_id": method_id,
            "calls": [{"generation": {"raw_output": "not inspected"}}],
            "final_parse": {"parse_status": "PARSED"},
            "resource_measurement": None,
        },
    }


def _write_checkpoint(root: Path, config: RunConfig, case_ids: tuple[str, ...]) -> Path:
    root.mkdir(parents=True)
    rows = [
        _row(config, case_id, method_id)
        for case_id in case_ids
        for method_id in config.methods
    ]
    results = "".join(
        json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n"
        for row in rows
    ).encode()
    run_config = (json.dumps(config.to_dict(), sort_keys=True) + "\n").encode()
    manifest = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "config_hash": config.config_hash,
        "row_count": len(rows),
        "files": {
            "results.jsonl": {
                "bytes": len(results),
                "sha256": hashlib.sha256(results).hexdigest(),
            },
            "run_config.json": {
                "bytes": len(run_config),
                "sha256": hashlib.sha256(run_config).hexdigest(),
            },
        },
    }
    archive_path = root / "checkpoint.zip"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in {
            "manifest.json": (json.dumps(manifest, sort_keys=True) + "\n").encode(),
            "results.jsonl": results,
            "run_config.json": run_config,
        }.items():
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, content)
    checkpoint_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    summary = {
        "status": "complete_accuracy_matrix_raw_results_unscored",
        "model_id": config.model_id,
        "model_revision": config.model_revision,
        "config_hash": config.config_hash,
        "expected_rows": len(rows),
        "results_sha256": hashlib.sha256(results).hexdigest(),
        "checkpoint_zip_sha256": checkpoint_sha,
        "scores_inspected": False,
        "matrix": {"complete": True, "expected_rows": len(rows)},
    }
    (root / "run_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return archive_path


class MultiUavAdmissionTests(unittest.TestCase):
    def test_admits_complete_sealed_checkpoint_without_outcome_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config = _config()
            case_ids = ("case-1", "case-2")
            root = Path(temporary) / "3b"
            checkpoint = _write_checkpoint(root, config, case_ids)

            report = admit_accuracy_checkpoint(
                checkpoint_path=checkpoint,
                run_summary_path=root / "run_summary.json",
                expected_config=config,
                expected_case_ids=case_ids,
            )

            self.assertTrue(report["valid"])
            self.assertEqual(report["rows"], 4)
            self.assertFalse(report["scores_inspected"])
            self.assertFalse(report["hidden_labels_accessed"])
            self.assertNotIn("parse_error_rows", report)
            self.assertEqual(len(report["run_summary_sha256"]), 64)

    def test_rejects_checkpoint_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config = _config()
            root = Path(temporary) / "3b"
            checkpoint = _write_checkpoint(root, config, ("case-1",))
            summary_path = root / "run_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["checkpoint_zip_sha256"] = "f" * 64
            summary_path.write_text(json.dumps(summary), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "checkpoint hash"):
                admit_accuracy_checkpoint(
                    checkpoint_path=checkpoint,
                    run_summary_path=summary_path,
                    expected_config=config,
                    expected_case_ids=("case-1",),
                )

    def test_study_admission_requires_every_registered_model(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "accuracy_manifest.json"
            manifest = {
                "case_count": 1,
                "cases": [
                    {
                        "case_id": "case-1",
                        "case_status": "approved_evaluation_case",
                    }
                ],
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            config_3b = RunConfig(
                **{**_config().payload(), "methods": _config().methods, "dataset_sha256": manifest_sha}
            )
            config_7b = RunConfig(
                **{
                    **_config("Qwen/Qwen2.5-7B-Instruct").payload(),
                    "methods": _config("Qwen/Qwen2.5-7B-Instruct").methods,
                    "dataset_sha256": manifest_sha,
                }
            )
            configs_path = root / "run_configs.json"
            configs_path.write_text(
                json.dumps(
                    {
                        "status": "final_accuracy_configs_bound_no_inference_started",
                        "accuracy_manifest_sha256": manifest_sha,
                        "expected_rows_per_model": 2,
                        "expected_rows_total": 4,
                        "configs": [config_3b.to_dict(), config_7b.to_dict()],
                    }
                ),
                encoding="utf-8",
            )
            checkpoint_3b = _write_checkpoint(root / "3b", config_3b, ("case-1",))

            with self.assertRaisesRegex(ValueError, "checkpoint models"):
                admit_accuracy_study(
                    manifest_path=manifest_path,
                    run_configs_path=configs_path,
                    checkpoint_paths=(checkpoint_3b,),
                )

    def test_cli_writes_combined_score_blind_admission_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "accuracy_manifest.json"
            manifest = {
                "case_count": 1,
                "cases": [
                    {
                        "case_id": "case-1",
                        "case_status": "approved_evaluation_case",
                    }
                ],
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            configs = []
            checkpoints = []
            for directory, model_id in (
                ("3b", "Qwen/Qwen2.5-3B-Instruct"),
                ("7b", "Qwen/Qwen2.5-7B-Instruct"),
            ):
                base = _config(model_id)
                config = RunConfig(
                    **{
                        **base.payload(),
                        "methods": base.methods,
                        "dataset_sha256": manifest_sha,
                    }
                )
                configs.append(config)
                checkpoints.append(
                    _write_checkpoint(root / directory, config, ("case-1",))
                )
            configs_path = root / "run_configs.json"
            configs_path.write_text(
                json.dumps(
                    {
                        "status": "final_accuracy_configs_bound_no_inference_started",
                        "accuracy_manifest_sha256": manifest_sha,
                        "expected_rows_per_model": 2,
                        "expected_rows_total": 4,
                        "configs": [config.to_dict() for config in configs],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "admission.json"
            command = [
                sys.executable,
                "scripts/admit_multiuav_accuracy_matrices.py",
                "--manifest",
                str(manifest_path),
                "--run-configs",
                str(configs_path),
                "--output",
                str(output),
            ]
            for checkpoint in checkpoints:
                command.extend(["--checkpoint", str(checkpoint)])

            subprocess.run(command, cwd=Path(__file__).parents[1], check=True)

            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                report["status"],
                "complete_accuracy_matrices_admitted_for_scoring",
            )
            self.assertEqual(report["rows_total"], 4)
            self.assertEqual(report["scored_rows"], 0)
            self.assertFalse(report["hidden_labels_accessed"])
            self.assertEqual(set(report["source_code_sha256"]), {
                "admit_multiuav_accuracy_matrices.py",
                "multiuav_admission.py",
                "multiuav_publication.py",
            })


if __name__ == "__main__":
    unittest.main()
