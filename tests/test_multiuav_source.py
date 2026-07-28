import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from shepherd_ai.multiuav_source import (
    PRIVILEGED_TASK_FIELDS,
    SOURCE_TEXT_FIELDS,
    audit_benchmark_archive,
)


ROOT = Path(__file__).resolve().parents[1]


def _task(task_id: str = "task-1") -> dict:
    return {
        "id": task_id,
        "name": "Take off and hover",
        "content": "Command Drone 1 to take off and hover.",
        "content_aliases": ["Have Drone 1 take off, then hover."],
        "difficulty": "easy",
        "related_apis": [{"endpoint": "/drones/1/take_off"}],
        "execution_check_apis": {
            "logic": "and",
            "checks": [
                {
                    "endpoint": "/check/airborne",
                    "parameters": {"drone_id": "1"},
                },
                {
                    "logic": "or",
                    "checks": [
                        {
                            "endpoint": "/check/hovering",
                            "parameters": {"drone_id": "1"},
                        },
                        {
                            "endpoint": "/check/stationary",
                            "parameters": {"drone_id": "1"},
                        },
                    ],
                },
            ],
        },
        "commands": ["take_off", "hover"],
        "is_done": False,
        "is_passed": False,
    }


def _session(tasks: list[dict] | None = None) -> dict:
    return {
        "id": "session-1",
        "name": "Area Search Easy 1",
        "task_type": "area_search",
        "drones": [],
        "targets": [],
        "obstacles": [],
        "environment": {},
        "tasks": tasks or [_task()],
    }


def _write_archive(
    path: Path,
    *,
    session: dict | None = None,
    include_image: bool = True,
) -> None:
    with ZipFile(path, "w") as bundle:
        bundle.writestr(
            "Area_Search_Easy_1_deadbeef.json",
            json.dumps(session or _session()),
        )
        if include_image:
            bundle.writestr("Area_Search_Easy_1_deadbeef.jpg", b"fixture")


class MultiUavSourceAuditTests(unittest.TestCase):
    def test_counts_nested_validation_leaves_and_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive = Path(temp_dir) / "benchmark.zip"
            _write_archive(archive)
            result = audit_benchmark_archive(
                archive,
                enforce_pinned_artifact=False,
            )

        self.assertEqual(result["counts"]["sessions"], 1)
        self.assertEqual(result["counts"]["tasks"], 1)
        self.assertEqual(result["counts"]["validation_check_leaves"], 3)
        self.assertEqual(result["counts"]["official_aliases"], 1)

    def test_rejects_unpaired_session_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive = Path(temp_dir) / "benchmark.zip"
            _write_archive(archive, include_image=False)

            with self.assertRaisesRegex(ValueError, "not paired"):
                audit_benchmark_archive(
                    archive,
                    enforce_pinned_artifact=False,
                )

    def test_rejects_duplicate_task_ids_across_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive = Path(temp_dir) / "benchmark.zip"
            with ZipFile(archive, "w") as bundle:
                for index in (1, 2):
                    session = _session()
                    session["id"] = f"session-{index}"
                    stem = f"Area_Search_Easy_{index}_deadbeef"
                    bundle.writestr(f"{stem}.json", json.dumps(session))
                    bundle.writestr(f"{stem}.jpg", b"fixture")

            with self.assertRaisesRegex(ValueError, "duplicate task id"):
                audit_benchmark_archive(
                    archive,
                    enforce_pinned_artifact=False,
                )

    def test_field_policy_separates_text_from_privileged_references(self) -> None:
        self.assertEqual(SOURCE_TEXT_FIELDS, {"id", "content", "content_aliases"})
        self.assertTrue(
            {
                "related_apis",
                "execution_check_apis",
                "commands",
                "is_done",
                "is_passed",
            }.issubset(PRIVILEGED_TASK_FIELDS)
        )
        self.assertTrue(SOURCE_TEXT_FIELDS.isdisjoint(PRIVILEGED_TASK_FIELDS))

    def test_pinned_mode_rejects_fixture_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive = Path(temp_dir) / "benchmark.zip"
            _write_archive(archive)

            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                audit_benchmark_archive(archive)

    def test_committed_registry_matches_preserved_audit(self) -> None:
        metadata = ROOT / "datasets" / "multiuav_plat"
        registry = json.loads(
            (metadata / "source_registry_v1.json").read_text(encoding="utf-8")
        )
        audit = json.loads(
            (metadata / "source_audit_v1.json").read_text(encoding="utf-8")
        )

        self.assertTrue(audit["valid"])
        self.assertEqual(
            registry["repository"]["commit"],
            audit["source"]["commit"],
        )
        self.assertEqual(
            registry["archive"]["sha256"],
            audit["benchmark"]["archive"]["sha256"],
        )
        self.assertEqual(
            registry["audit"]["session_count"],
            audit["benchmark"]["counts"]["sessions"],
        )
        self.assertEqual(
            registry["audit"]["task_count"],
            audit["benchmark"]["counts"]["tasks"],
        )
        self.assertEqual(
            registry["audit"]["validation_check_leaf_count"],
            audit["benchmark"]["counts"]["validation_check_leaves"],
        )
        self.assertEqual(
            registry["field_policy"]["privileged_task_fields_forbidden_in_model_prompts"],
            audit["benchmark"]["field_policy"]["privileged_task_fields"],
        )


if __name__ == "__main__":
    unittest.main()
