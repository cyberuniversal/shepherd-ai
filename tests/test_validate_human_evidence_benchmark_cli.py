import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_human_evidence_benchmark.py"


def _record(record_id: str, text: str, decision: str) -> dict:
    return {
        "id": record_id,
        "text": text,
        "decision_stage": "grounding_sufficiency",
        "context_id": f"context_{record_id}",
        "expected_decision": decision,
        "label_rationale": "Human reviewer verified the registered context.",
        "split": "final_test",
        "source": "manual_week9_evidence_collection_v1",
        "data_type": "human_written_evidence_decision",
        "author_id": f"author_{record_id}",
        "reviewer_id": f"reviewer_{record_id}",
        "label_status": "adjudicated",
    }


def _context() -> dict:
    return {
        "context_id": "context_001",
        "decision_stage": "grounding_sufficiency",
        "stage_definition": "Resolve each reference uniquely.",
        "evidence": {"map_records": [{"id": "alpha"}]},
        "source": "manual_week9_context_collection_v1",
        "data_type": "registered_simulation_evidence_context",
    }


class ValidateHumanEvidenceBenchmarkCliTests(unittest.TestCase):
    def test_accepts_balanced_adjudicated_nonoverlapping_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            dataset = temp / "candidate.jsonl"
            summary = temp / "summary.json"
            _write_jsonl(
                dataset,
                [
                    _record("001", "Inspect the alpha parcel.", "proceed"),
                    _record("002", "Inspect the unspecified lane.", "clarify"),
                    _record("003", "Enter the forbidden depot.", "block"),
                ],
            )
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--dataset",
                    str(dataset),
                    "--summary-output",
                    str(summary),
                    "--require-balanced",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(summary.read_text(encoding="utf-8"))

        self.assertTrue(payload["valid"])
        self.assertEqual(payload["record_count"], 3)

    def test_rejects_overlap_and_self_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            comparison = temp / "existing.jsonl"
            candidate = temp / "candidate.jsonl"
            summary = temp / "summary.json"
            _write_jsonl(comparison, [{"text": "Inspect the alpha parcel."}])
            rows = [
                _record("001", "Inspect the alpha parcel.", "proceed"),
                _record("002", "Inspect the unspecified lane.", "clarify"),
                _record("003", "Enter the forbidden depot.", "block"),
            ]
            rows[0]["reviewer_id"] = rows[0]["author_id"]
            _write_jsonl(candidate, rows)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--dataset",
                    str(candidate),
                    "--comparison",
                    str(comparison),
                    "--summary-output",
                    str(summary),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            payload = json.loads(summary.read_text(encoding="utf-8"))

        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(payload["valid"])
        self.assertTrue(
            any("overlaps" in error for error in payload["errors"])
        )
        self.assertTrue(
            any("must differ" in error for error in payload["errors"])
        )

    def test_validates_frozen_context_hash_when_contexts_are_supplied(self) -> None:
        from shepherd_ai.human_evidence_benchmark import context_sha256

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            contexts = temp / "contexts.jsonl"
            candidate = temp / "candidate.jsonl"
            summary = temp / "summary.json"
            context = _context()
            _write_jsonl(contexts, [context])
            rows = [
                _record("001", "Inspect the alpha parcel.", "proceed"),
                _record("002", "Inspect the unspecified lane.", "clarify"),
                _record("003", "Enter the forbidden depot.", "block"),
            ]
            for row in rows:
                row["context_id"] = "context_001"
                row["context_sha256"] = context_sha256(context)
            _write_jsonl(candidate, rows)
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--dataset",
                    str(candidate),
                    "--contexts",
                    str(contexts),
                    "--summary-output",
                    str(summary),
                    "--require-balanced",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(summary.read_text(encoding="utf-8"))

        self.assertTrue(payload["valid"])
        self.assertTrue(payload["frozen_contexts_validated"])


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
