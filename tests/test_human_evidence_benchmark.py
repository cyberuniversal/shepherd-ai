import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from shepherd_ai.human_evidence_benchmark import (
    adjudicate_records,
    build_model_packet,
    index_contexts,
    prepare_blinded_review,
)


ROOT = Path(__file__).resolve().parents[1]


def _context() -> dict:
    return {
        "context_id": "context_001",
        "decision_stage": "grounding_sufficiency",
        "stage_definition": "Resolve every reference uniquely against the map.",
        "evidence": {"map_records": [{"id": "field_alpha", "name": "Alpha Field"}]},
        "source": "manual_week9_context_collection_v1",
        "data_type": "registered_simulation_evidence_context",
    }


def _author(decision: str = "proceed") -> dict:
    return {
        "id": "evidence_human_001",
        "text": "Examine Alpha Field for damaged plants.",
        "decision_stage": "grounding_sufficiency",
        "context_id": "context_001",
        "author_decision": decision,
        "author_rationale": "Alpha Field has one matching map record.",
        "split": "final_test",
        "source": "manual_week9_evidence_collection_v1",
        "data_type": "human_written_evidence_decision",
        "author_id": "participant_001",
    }


def _review(decision: str = "proceed") -> dict:
    return {
        "id": "evidence_human_001",
        "reviewer_id": "reviewer_001",
        "reviewer_decision": decision,
        "reviewer_rationale": "The supplied map resolves the location uniquely.",
    }


class HumanEvidenceBenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contexts = index_contexts([_context()])

    def test_review_packet_is_blinded_and_binds_context(self) -> None:
        packet = prepare_blinded_review([_author()], self.contexts)

        self.assertEqual(len(packet), 1)
        self.assertNotIn("author_decision", packet[0])
        self.assertNotIn("author_rationale", packet[0])
        self.assertNotIn("author_id", packet[0])
        self.assertEqual(packet[0]["evidence"]["map_records"][0]["id"], "field_alpha")
        self.assertEqual(len(packet[0]["context_sha256"]), 64)

    def test_agreement_produces_adjudicated_record(self) -> None:
        final_rows, disagreements = adjudicate_records(
            [_author()], [_review()], self.contexts
        )

        self.assertEqual(disagreements, [])
        self.assertEqual(final_rows[0]["expected_decision"], "proceed")
        self.assertEqual(final_rows[0]["label_status"], "adjudicated")
        self.assertEqual(final_rows[0]["label_resolution"], "independent_agreement")

    def test_disagreement_requires_distinct_third_party(self) -> None:
        final_rows, disagreements = adjudicate_records(
            [_author("proceed")], [_review("clarify")], self.contexts
        )

        self.assertEqual(final_rows, [])
        self.assertEqual(
            disagreements[0]["status"], "requires_third_party_adjudication"
        )

        final_rows, _ = adjudicate_records(
            [_author("proceed")],
            [_review("clarify")],
            self.contexts,
            [
                {
                    "id": "evidence_human_001",
                    "adjudicator_id": "adjudicator_001",
                    "final_decision": "clarify",
                    "adjudication_rationale": "The target term lacks a unique match.",
                }
            ],
        )
        self.assertEqual(final_rows[0]["expected_decision"], "clarify")
        self.assertEqual(
            final_rows[0]["label_resolution"], "third_party_adjudication"
        )

    def test_model_packet_separates_gold_and_annotation_metadata(self) -> None:
        final_rows, _ = adjudicate_records([_author()], [_review()], self.contexts)
        inputs, gold = build_model_packet(final_rows, self.contexts)

        self.assertNotIn("expected_decision", inputs[0])
        self.assertNotIn("label_rationale", inputs[0])
        self.assertNotIn("reviewer_id", inputs[0])
        self.assertEqual(gold[0]["expected_decision"], "proceed")
        self.assertEqual(inputs[0]["prompt_sha256"], inputs[0]["prompt_sha256"])

    def test_changed_context_is_rejected_after_adjudication(self) -> None:
        final_rows, _ = adjudicate_records([_author()], [_review()], self.contexts)
        changed = _context()
        changed["evidence"]["map_records"].append(
            {"id": "field_beta", "name": "Beta Field"}
        )

        with self.assertRaisesRegex(ValueError, "frozen context hash mismatch"):
            build_model_packet(final_rows, index_contexts([changed]))

    def test_model_packet_rejects_record_that_is_not_adjudicated(self) -> None:
        final_rows, _ = adjudicate_records([_author()], [_review()], self.contexts)
        final_rows[0]["label_status"] = "draft"

        with self.assertRaisesRegex(ValueError, "label_status"):
            build_model_packet(final_rows, self.contexts)

    def test_rejects_adjudication_without_disagreement(self) -> None:
        with self.assertRaisesRegex(ValueError, "without disagreement"):
            adjudicate_records(
                [_author()],
                [_review()],
                self.contexts,
                [
                    {
                        "id": "evidence_human_001",
                        "adjudicator_id": "adjudicator_001",
                        "final_decision": "proceed",
                        "adjudication_rationale": "No disagreement existed.",
                    }
                ],
            )


class HumanEvidenceBenchmarkCliTests(unittest.TestCase):
    def test_prepares_adjudicates_and_builds_label_separated_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            contexts = temp / "contexts.jsonl"
            authors = temp / "authors.jsonl"
            reviews = temp / "reviews.jsonl"
            blind = temp / "blind.jsonl"
            blind_manifest = temp / "blind_manifest.json"
            benchmark = temp / "benchmark.jsonl"
            disagreements = temp / "disagreements.jsonl"
            adjudication_summary = temp / "adjudication_summary.json"
            inputs = temp / "inputs.jsonl"
            gold = temp / "gold.jsonl"
            packet_manifest = temp / "packet_manifest.json"
            _write_jsonl(contexts, [_context()])
            _write_jsonl(authors, [_author()])
            _write_jsonl(reviews, [_review()])

            _run_script(
                "prepare_human_evidence_review.py",
                "--author-dataset", authors,
                "--contexts", contexts,
                "--output", blind,
                "--manifest-output", blind_manifest,
            )
            _run_script(
                "adjudicate_human_evidence_benchmark.py",
                "--author-dataset", authors,
                "--review-dataset", reviews,
                "--contexts", contexts,
                "--output", benchmark,
                "--disagreements-output", disagreements,
                "--summary-output", adjudication_summary,
            )
            _run_script(
                "build_human_evidence_model_packet.py",
                "--benchmark", benchmark,
                "--contexts", contexts,
                "--inputs-output", inputs,
                "--gold-output", gold,
                "--manifest-output", packet_manifest,
            )

            blind_row = _read_first(blind)
            input_row = _read_first(inputs)
            gold_row = _read_first(gold)
            summary = json.loads(adjudication_summary.read_text(encoding="utf-8"))

        self.assertNotIn("author_decision", blind_row)
        self.assertNotIn("expected_decision", input_row)
        self.assertEqual(gold_row["expected_decision"], "proceed")
        self.assertTrue(summary["complete"])


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _read_first(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8").splitlines()[0])


def _run_script(script: str, *args: object) -> None:
    command = [sys.executable, str(ROOT / "scripts" / script)]
    command.extend(str(arg) for arg in args)
    subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


if __name__ == "__main__":
    unittest.main()
