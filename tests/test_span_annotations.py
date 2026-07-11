import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.span_annotations import (  # noqa: E402
    build_spans_from_phrases,
    load_span_labeled_commands,
    spans_to_bio_tags,
    summarize_span_labeled_commands,
    tokenize_with_offsets,
)


class SpanAnnotationTests(unittest.TestCase):
    def test_load_span_labeled_commands_validates_offsets_and_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spans.jsonl"
            text = "Send the nearest drone to inspect the livestock pen."
            start = text.index("livestock pen")
            end = start + len("livestock pen")
            path.write_text(
                json.dumps(
                    {
                        "id": "span_cmd_001",
                        "text": text,
                        "split": "train",
                        "source": "manual_week2_span_annotation_v1",
                        "data_type": "human_verified_span_command",
                        "spans": [
                            {
                                "field": "target",
                                "start": start,
                                "end": end,
                                "text": "livestock pen",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            records = load_span_labeled_commands(path)

        self.assertEqual(records[0].id, "span_cmd_001")
        self.assertEqual(records[0].spans[0].field, "target")
        self.assertEqual(records[0].spans[0].text, "livestock pen")

    def test_load_span_labeled_commands_rejects_mismatched_span_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad_spans.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "id": "span_cmd_001",
                        "text": "Inspect the livestock pen.",
                        "split": "train",
                        "source": "manual_week2_span_annotation_v1",
                        "data_type": "human_verified_span_command",
                        "spans": [
                            {"field": "target", "start": 12, "end": 25, "text": "greenhouse"}
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_span_labeled_commands(path)

    def test_load_span_labeled_commands_accepts_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spans.jsonl"
            text = "Inspect the greenhouse."
            start = text.index("greenhouse")
            payload = {
                "id": "span_cmd_001",
                "text": text,
                "split": "train",
                "source": "manual_week2_span_annotation_v1",
                "data_type": "human_verified_span_command",
                "spans": [
                    {
                        "field": "target",
                        "start": start,
                        "end": start + len("greenhouse"),
                        "text": "greenhouse",
                    }
                ],
            }
            path.write_text(json.dumps(payload) + "\n", encoding="utf-8-sig")

            records = load_span_labeled_commands(path)

        self.assertEqual(records[0].spans[0].text, "greenhouse")

    def test_tokenize_with_offsets_preserves_character_positions(self) -> None:
        tokens = tokenize_with_offsets("Capture images of the red pickup truck.")

        self.assertEqual(tokens[0].text, "Capture")
        self.assertEqual(tokens[0].start, 0)
        self.assertEqual(tokens[-1].text, ".")
        self.assertEqual(tokens[-1].end, len("Capture images of the red pickup truck."))

    def test_spans_to_bio_tags_marks_target_tokens(self) -> None:
        text = "Capture images of the red pickup truck."
        start = text.index("red pickup truck")
        end = start + len("red pickup truck")

        tagged = spans_to_bio_tags(
            text,
            [{"field": "target", "start": start, "end": end, "text": "red pickup truck"}],
        )

        by_text = [(token.text, tag) for token, tag in tagged]
        self.assertIn(("red", "B-target"), by_text)
        self.assertIn(("pickup", "I-target"), by_text)
        self.assertIn(("truck", "I-target"), by_text)
        self.assertEqual(by_text[0], ("Capture", "O"))

    def test_build_spans_from_phrases_matches_case_insensitively_and_preserves_text(self) -> None:
        spans = build_spans_from_phrases(
            "Send two drones north and inspect the crops.",
            [("action", "send"), ("target", "CROPS")],
        )

        self.assertEqual(
            spans,
            [
                {"field": "action", "start": 0, "end": 4, "text": "Send"},
                {"field": "target", "start": 38, "end": 43, "text": "crops"},
            ],
        )

    def test_spans_to_bio_tags_rejects_overlapping_spans(self) -> None:
        text = "Scan the north loading dock."

        with self.assertRaises(ValueError):
            spans_to_bio_tags(
                text,
                [
                    {"field": "location", "start": 9, "end": 14, "text": "north"},
                    {"field": "target", "start": 9, "end": 27, "text": "north loading dock"},
                ],
            )

    def test_summarize_span_labeled_commands_reports_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spans.jsonl"
            text = "Scan the loading dock without crossing the road."
            target_start = text.index("loading dock")
            constraint_start = text.index("without crossing the road")
            records = [
                {
                    "id": "span_cmd_001",
                    "text": text,
                    "split": "validation",
                    "source": "manual_week2_span_annotation_v1",
                    "data_type": "human_verified_span_command",
                    "spans": [
                        {
                            "field": "target",
                            "start": target_start,
                            "end": target_start + len("loading dock"),
                            "text": "loading dock",
                        },
                        {
                            "field": "constraint",
                            "start": constraint_start,
                            "end": constraint_start + len("without crossing the road"),
                            "text": "without crossing the road",
                        },
                    ],
                }
            ]
            path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

            summary = summarize_span_labeled_commands(load_span_labeled_commands(path))

        self.assertEqual(summary["records"], 1)
        self.assertEqual(summary["split_counts"], {"validation": 1})
        self.assertEqual(summary["span_field_counts"], {"constraint": 1, "target": 1})


if __name__ == "__main__":
    unittest.main()
