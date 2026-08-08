import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from shepherd_ai.multiuav_checkpoints import RunConfig
from shepherd_ai.multiuav_study_scoring import (
    validate_admission_for_scoring,
    write_scored_rows_archive,
)


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _config() -> RunConfig:
    return RunConfig(
        run_id="accuracy-test",
        study_id="multiuav_validation_placement_v1",
        run_kind="accuracy",
        model_id="Qwen/Qwen2.5-3B-Instruct",
        model_revision="aa8e72537993ba99e69dfaafa59ed015b17504d1",
        methods=("M1_monolithic", "M3_stage_wise"),
        dataset_sha256="a" * 64,
        prompt_contract_version="multiuav_prompt_contract_v1",
        decoding={"do_sample": False, "num_beams": 1, "max_new_tokens": 512},
        code_commit="b" * 40,
    )


def _write_gate(root: Path) -> tuple[Path, Path, Path, Path]:
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps({"cases": []}), encoding="utf-8")
    config = _config()
    configs_path = root / "configs.json"
    configs_path.write_text(
        json.dumps(
            {
                "status": "final_accuracy_configs_bound_no_inference_started",
                "expected_rows_per_model": 2,
                "expected_rows_total": 2,
                "configs": [config.to_dict()],
            }
        ),
        encoding="utf-8",
    )
    checkpoint_path = root / "checkpoint.zip"
    checkpoint_path.write_bytes(b"sealed-checkpoint")
    admission_path = root / "admission.json"
    admission_path.write_text(
        json.dumps(
            {
                "status": "complete_accuracy_matrices_admitted_for_scoring",
                "valid": True,
                "next_gate": (
                    "label_separated_deterministic_scoring_authorized_not_started"
                ),
                "scores_inspected": False,
                "hidden_labels_accessed": False,
                "scored_rows": 0,
                "artifact_bindings": {
                    "accuracy_manifest_sha256": _sha256(manifest_path),
                    "accuracy_run_configs_sha256": _sha256(configs_path),
                },
                "source_code_sha256": {
                    "multiuav_admission.py": _sha256(
                        ROOT / "src/shepherd_ai/multiuav_admission.py"
                    ),
                    "multiuav_publication.py": _sha256(
                        ROOT / "src/shepherd_ai/multiuav_publication.py"
                    ),
                    "admit_multiuav_accuracy_matrices.py": _sha256(
                        ROOT / "scripts/admit_multiuav_accuracy_matrices.py"
                    ),
                },
                "matrices": [
                    {
                        "valid": True,
                        "model_id": config.model_id,
                        "model_revision": config.model_revision,
                        "config_hash": config.config_hash,
                        "checkpoint_sha256": _sha256(checkpoint_path),
                        "results_sha256": "c" * 64,
                        "rows": 2,
                        "scores_inspected": False,
                        "hidden_labels_accessed": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return admission_path, manifest_path, configs_path, checkpoint_path


class MultiUavStudyScoringTests(unittest.TestCase):
    def test_admission_gate_binds_checkpoint_before_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            admission, manifest, configs, checkpoint = _write_gate(root)

            gate = validate_admission_for_scoring(
                repository_root=ROOT,
                admission_path=admission,
                manifest_path=manifest,
                run_configs_path=configs,
                checkpoint_paths=(checkpoint,),
            )

            self.assertEqual(set(gate["configs"]), {"Qwen/Qwen2.5-3B-Instruct"})
            self.assertEqual(gate["checkpoints"]["Qwen/Qwen2.5-3B-Instruct"], checkpoint)

    def test_admission_gate_rejects_checkpoint_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            admission, manifest, configs, checkpoint = _write_gate(root)
            checkpoint.write_bytes(b"mutated")

            with self.assertRaisesRegex(ValueError, "checkpoint hash"):
                validate_admission_for_scoring(
                    repository_root=ROOT,
                    admission_path=admission,
                    manifest_path=manifest,
                    run_configs_path=configs,
                    checkpoint_paths=(checkpoint,),
                )

    def test_derived_rows_archive_is_deterministic_and_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.zip"
            second = root / "second.zip"
            rows = [{"case_id": "case-1", "metric": True}]
            metadata = {"model_id": "synthetic", "rows": 1}

            first_record = write_scored_rows_archive(
                rows=rows,
                output_path=first,
                metadata=metadata,
            )
            second_record = write_scored_rows_archive(
                rows=rows,
                output_path=second,
                metadata=metadata,
            )

            self.assertEqual(first_record["sha256"], second_record["sha256"])
            with ZipFile(first) as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {"manifest.json", "scored_rows.jsonl", "scoring_metadata.json"},
                )
                manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["row_count"], 1)


if __name__ == "__main__":
    unittest.main()
