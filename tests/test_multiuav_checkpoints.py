import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from shepherd_ai.multiuav_checkpoints import (
    JsonlCheckpoint,
    RunConfig,
    create_compact_checkpoint_zip,
    expected_result_keys,
)
from shepherd_ai.multiuav_context import project_agent_visible_context
from shepherd_ai.multiuav_experiment import EvaluationCase, run_case_matrix
from shepherd_ai.multiuav_prompts import PROMPT_CONTRACT_VERSION
from shepherd_ai.multiuav_runner import GenerationResult


def _config(**changes) -> RunConfig:
    values = {
        "run_id": "synthetic-smoke-v1",
        "study_id": "multiuav_validation_placement_v1",
        "run_kind": "synthetic_smoke",
        "model_id": "Qwen/Qwen2.5-3B-Instruct",
        "model_revision": "aa8e72537993ba99e69dfaafa59ed015b17504d1",
        "methods": ("M1_monolithic", "M2_post_plan_deterministic"),
        "dataset_sha256": "a" * 64,
        "prompt_contract_version": PROMPT_CONTRACT_VERSION,
        "decoding": {
            "do_sample": False,
            "num_beams": 1,
            "max_new_tokens": 512,
        },
        "code_commit": "b" * 40,
    }
    values.update(changes)
    return RunConfig(**values)


def _context(task_id: str) -> dict:
    return project_agent_visible_context(
        {
            "id": "session-1",
            "task_type": "area_search",
            "canvas_width": 100,
            "canvas_height": 80,
            "status": "active",
            "drones": [
                {
                    "id": "drone-1",
                    "name": "Drone 1",
                    "status": "idle",
                    "position": {"x": 0, "y": 0, "z": 0},
                    "max_altitude": 50,
                }
            ],
            "environment": {"id": "env-1", "weather": "clear"},
        },
        task_id=task_id,
        instruction="Have Drone 1 hover.",
    )


def _output() -> str:
    return json.dumps(
        {
            "decision": "EXECUTE",
            "reason": "Visible drone can hover.",
            "clarification_question": None,
            "api_plan": [
                {
                    "endpoint": "/drones/{id}/command/hover",
                    "parameters": {"id": "drone-1"},
                }
            ],
        }
    )


class _Backend:
    def __init__(self, output_count: int) -> None:
        self.remaining = output_count
        self.calls = 0

    def generate(self, request):
        if self.remaining <= 0:
            raise AssertionError("unexpected generation")
        self.remaining -= 1
        self.calls += 1
        return GenerationResult(
            raw_output=_output(),
            metadata={"backend": "synthetic_checkpoint_fixture"},
        )


class _ResourceMonitor:
    def measure(self, operation):
        return operation(), {
            "schema_version": 1,
            "valid": True,
            "energy": {"scope": "nvidia_gpu_board_only", "joules": 1.25},
        }


class MultiUavCheckpointTests(unittest.TestCase):
    def test_run_config_rejects_mutable_or_nondeterministic_settings(self) -> None:
        with self.assertRaisesRegex(ValueError, "frozen registry"):
            _config(model_revision="main").validate()
        with self.assertRaisesRegex(ValueError, "do_sample=false"):
            _config(
                decoding={
                    "do_sample": True,
                    "num_beams": 1,
                    "max_new_tokens": 512,
                }
            ).validate()
        with self.assertRaisesRegex(ValueError, "repetition"):
            _config(run_kind="resource").validate()
        with self.assertRaisesRegex(ValueError, "only valid for resource"):
            _config(resource_repetition=1).validate()

    def test_resource_run_requires_monitor_and_checkpoints_measurement(self) -> None:
        config = _config(
            run_kind="resource",
            resource_repetition=1,
            hardware_protocol_sha256="c" * 64,
            resource_condition_order=1,
            resource_schedule_sha256="d" * 64,
            methods=("M1_monolithic",),
        )
        cases = (
            EvaluationCase("case-1", "synthetic_unit_fixture", _context("task-1")),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint = JsonlCheckpoint(
                Path(temp_dir) / "results.jsonl",
                config,
            )
            with self.assertRaisesRegex(ValueError, "monitor factory"):
                run_case_matrix(
                    config=config,
                    cases=cases,
                    backend=_Backend(output_count=1),
                    checkpoint=checkpoint,
                )
            result = run_case_matrix(
                config=config,
                cases=cases,
                backend=_Backend(output_count=1),
                checkpoint=checkpoint,
                resource_monitor_factory=_ResourceMonitor,
            )
            row = checkpoint.load_rows()[0]

        self.assertTrue(result["resource_measurement_enabled"])
        self.assertTrue(row["result"]["resource_measurement"]["valid"])
        self.assertEqual(
            row["result"]["resource_measurement"]["energy"]["joules"],
            1.25,
        )

    def test_matrix_checkpoints_every_row_and_resumes_without_calls(self) -> None:
        cases = (
            EvaluationCase("case-1", "synthetic_unit_fixture", _context("task-1")),
            EvaluationCase("case-2", "synthetic_unit_fixture", _context("task-2")),
        )
        config = _config()
        with tempfile.TemporaryDirectory() as temp_dir:
            results = Path(temp_dir) / "results.jsonl"
            archive = Path(temp_dir) / "checkpoint.zip"
            checkpoint = JsonlCheckpoint(results, config)
            backend = _Backend(output_count=4)
            progress = []
            first = run_case_matrix(
                config=config,
                cases=cases,
                backend=backend,
                checkpoint=checkpoint,
                compact_zip_path=archive,
                compact_every_rows=2,
                progress_callback=progress.append,
            )
            resumed_backend = _Backend(output_count=0)
            second = run_case_matrix(
                config=config,
                cases=cases,
                backend=resumed_backend,
                checkpoint=checkpoint,
                compact_zip_path=archive,
            )

            rows = checkpoint.load_rows()
            with zipfile.ZipFile(archive) as zipped:
                names = set(zipped.namelist())

        self.assertEqual(first["appended_rows"], 4)
        self.assertEqual(
            [row["completed_rows"] for row in progress],
            [1, 2, 3, 4],
        )
        self.assertEqual(second["appended_rows"], 0)
        self.assertEqual(second["resumed_rows"], 4)
        self.assertEqual(len(rows), 4)
        self.assertEqual(
            names,
            {"manifest.json", "results.jsonl", "run_config.json"},
        )
        self.assertEqual(resumed_backend.calls, 0)

    def test_incompatible_resume_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "results.jsonl"
            JsonlCheckpoint(path, _config()).initialize()
            changed = JsonlCheckpoint(
                path,
                _config(dataset_sha256="c" * 64),
            )

            with self.assertRaisesRegex(ValueError, "incompatible resume"):
                changed.initialize()

    def test_duplicate_or_incomplete_matrix_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "results.jsonl"
            checkpoint = JsonlCheckpoint(path, _config())
            checkpoint.initialize()

            with self.assertRaisesRegex(ValueError, "matrix mismatch"):
                checkpoint.assert_complete(
                    expected_result_keys(
                        ["case-1"],
                        ["M1_monolithic"],
                    )
                )

    def test_compact_archive_is_deterministic_for_unchanged_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint = JsonlCheckpoint(
                Path(temp_dir) / "results.jsonl",
                _config(),
            )
            checkpoint.initialize()
            first = Path(temp_dir) / "first.zip"
            second = Path(temp_dir) / "second.zip"
            first_result = create_compact_checkpoint_zip(checkpoint, first)
            second_result = create_compact_checkpoint_zip(checkpoint, second)

        self.assertEqual(
            first_result["archive_sha256"],
            second_result["archive_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
