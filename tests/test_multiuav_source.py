import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from shepherd_ai.multiuav_source import (
    PRIVILEGED_TASK_FIELDS,
    SOURCE_TEXT_FIELDS,
    audit_instruction_overlap,
    audit_benchmark_archive,
    build_stratified_session_split,
    build_task_eligibility,
    summarize_task_eligibility,
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

    def test_committed_split_is_bound_to_source_and_balanced(self) -> None:
        metadata = ROOT / "datasets" / "multiuav_plat"
        registry = json.loads(
            (metadata / "source_registry_v1.json").read_text(encoding="utf-8")
        )
        split = json.loads(
            (metadata / "session_split_v1.json").read_text(encoding="utf-8")
        )

        self.assertEqual(
            split["source_archive_sha256"],
            registry["archive"]["sha256"],
        )
        self.assertEqual(
            split["session_counts"],
            {"train": 45, "calibration": 15, "test": 15},
        )
        self.assertEqual(len(split["assignments"]), 75)
        self.assertEqual(len(split["stratum_split_counts"]), 15)
        self.assertTrue(
            all(
                counts == {"train": 3, "calibration": 1, "test": 1}
                for counts in split["stratum_split_counts"].values()
            )
        )

    def test_committed_eligibility_is_bound_and_has_no_overlap(self) -> None:
        import hashlib

        metadata = ROOT / "datasets" / "multiuav_plat"
        split_path = metadata / "session_split_v1.json"
        eligibility = json.loads(
            (metadata / "task_eligibility_v1.json").read_text(encoding="utf-8")
        )

        split_sha256 = hashlib.sha256(split_path.read_bytes()).hexdigest()
        self.assertEqual(eligibility["session_split_sha256"], split_sha256)
        self.assertEqual(eligibility["summary"]["eligible_task_count"], 1_473)
        self.assertEqual(eligibility["summary"]["excluded_task_count"], 27)
        self.assertEqual(
            eligibility["summary"]["five_case_variant_count"],
            7_365,
        )
        self.assertEqual(
            eligibility["summary"]["normalized_cross_split_overlap_count"],
            0,
        )


class MultiUavSessionSplitTests(unittest.TestCase):
    def test_split_is_deterministic_and_balanced_per_stratum(self) -> None:
        records = _split_records()

        first = build_stratified_session_split(records, seed="registered-seed")
        second = build_stratified_session_split(
            list(reversed(records)),
            seed="registered-seed",
        )

        self.assertEqual(first, second)
        for scenario in ("area_search", "target_assignment"):
            rows = [row for row in first if row["scenario"] == scenario]
            self.assertEqual(
                {split: sum(row["split"] == split for row in rows) for split in (
                    "train",
                    "calibration",
                    "test",
                )},
                {"train": 3, "calibration": 1, "test": 1},
            )

    def test_split_rejects_incomplete_stratum(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected 5"):
            build_stratified_session_split(
                _split_records()[:-1],
                seed="registered-seed",
            )

    def test_overlap_audit_reports_cross_split_tasks(self) -> None:
        records = _split_records()
        assignments = build_stratified_session_split(
            records,
            seed="registered-seed",
        )
        split_by_id = {
            row["session_id"]: row["split"]
            for row in assignments
        }
        first = records[0]
        other = next(
            record
            for record in records
            if split_by_id[record["session_id"]]
            != split_by_id[first["session_id"]]
        )
        other["tasks"][0]["canonical_normalized"] = (
            first["tasks"][0]["canonical_normalized"]
        )

        overlap = audit_instruction_overlap(records, assignments)

        self.assertEqual(
            overlap["canonical"]["cross_split_normalized_text_count"],
            1,
        )
        self.assertEqual(
            overlap["canonical"]["cross_split_affected_task_count"],
            2,
        )


class MultiUavTaskEligibilityTests(unittest.TestCase):
    def test_maximum_support_ownership_minimizes_canonical_exclusions(self) -> None:
        records, assignments = _eligibility_records()

        rows = build_task_eligibility(
            records,
            assignments,
            seed="eligibility-seed",
        )
        summary = summarize_task_eligibility(rows)

        excluded = [row for row in rows if not row["eligible"]]
        self.assertEqual(len(excluded), 1)
        self.assertEqual(excluded[0]["split"], "test")
        self.assertEqual(
            excluded[0]["exclusion_reason"],
            "cross_split_canonical_nonowner",
        )
        self.assertEqual(summary["normalized_cross_split_overlap_count"], 0)

    def test_alias_owner_uses_support_and_falls_back_to_unique_alias(self) -> None:
        records, assignments = _eligibility_records()

        rows = build_task_eligibility(
            records,
            assignments,
            seed="eligibility-seed",
        )
        indexed = {row["task_id"]: row for row in rows}

        self.assertEqual(
            indexed["calibration-unique"]["selected_alias_normalized"],
            "calibration only alias",
        )
        self.assertTrue(indexed["train-alias-1"]["eligible"])
        self.assertTrue(indexed["train-alias-2"]["eligible"])

    def test_eligibility_is_independent_of_source_record_order(self) -> None:
        records, assignments = _eligibility_records()

        first = build_task_eligibility(
            records,
            assignments,
            seed="eligibility-seed",
        )
        second = build_task_eligibility(
            list(reversed(records)),
            list(reversed(assignments)),
            seed="eligibility-seed",
        )

        self.assertEqual(first, second)


def _split_records() -> list[dict]:
    records = []
    for scenario in ("area_search", "target_assignment"):
        for index in range(5):
            session_id = f"{scenario}-{index}"
            records.append(
                {
                    "session_id": session_id,
                    "archive_member": f"{session_id}.json",
                    "scenario": scenario,
                    "difficulty": "easy",
                    "tasks": [
                        {
                            "task_id": f"task-{session_id}",
                            "canonical_normalized": f"canonical {session_id}",
                            "aliases_normalized": [f"alias {session_id}"],
                        }
                    ],
                }
            )
    return records


def _eligibility_task(
    task_id: str,
    canonical: str,
    aliases: list[str],
) -> dict:
    return {
        "task_id": task_id,
        "canonical_text": canonical,
        "canonical_normalized": canonical,
        "aliases": aliases,
        "aliases_normalized": aliases,
    }


def _eligibility_records() -> tuple[list[dict], list[dict]]:
    sessions = [
        {
            "session_id": "train-1",
            "archive_member": "train-1.json",
            "scenario": "area_search",
            "difficulty": "easy",
            "tasks": [
                _eligibility_task(
                    "train-shared-1",
                    "shared canonical",
                    ["train shared canonical alias"],
                ),
                _eligibility_task(
                    "train-alias-1",
                    "train canonical one",
                    ["shared alias"],
                ),
            ],
        },
        {
            "session_id": "train-2",
            "archive_member": "train-2.json",
            "scenario": "area_search",
            "difficulty": "easy",
            "tasks": [
                _eligibility_task(
                    "train-shared-2",
                    "shared canonical",
                    ["train shared canonical alias two"],
                ),
                _eligibility_task(
                    "train-alias-2",
                    "train canonical two",
                    ["shared alias"],
                ),
            ],
        },
        {
            "session_id": "test-1",
            "archive_member": "test-1.json",
            "scenario": "area_search",
            "difficulty": "easy",
            "tasks": [
                _eligibility_task(
                    "test-shared",
                    "shared canonical",
                    ["test shared canonical alias"],
                ),
            ],
        },
        {
            "session_id": "calibration-1",
            "archive_member": "calibration-1.json",
            "scenario": "area_search",
            "difficulty": "easy",
            "tasks": [
                _eligibility_task(
                    "calibration-unique",
                    "calibration canonical",
                    ["shared alias", "calibration only alias"],
                ),
            ],
        },
    ]
    split_by_session = {
        "train-1": "train",
        "train-2": "train",
        "test-1": "test",
        "calibration-1": "calibration",
    }
    assignments = [
        {
            "session_id": record["session_id"],
            "split": split_by_session[record["session_id"]],
        }
        for record in sessions
    ]
    return sessions, assignments


if __name__ == "__main__":
    unittest.main()
