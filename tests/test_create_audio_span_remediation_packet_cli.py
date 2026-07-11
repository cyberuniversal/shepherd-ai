import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_audio_span_remediation_packet.py"


class CreateAudioSpanRemediationPacketCliTests(unittest.TestCase):
    def test_cli_creates_blank_span_packet_from_failed_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evaluation = root / "evaluation.json"
            evaluation.write_text(
                json.dumps(
                    {
                        "records": [
                            _eval_record("audio_001", False, ["location", "target"]),
                            _eval_record("audio_002", True, []),
                            {**_eval_record("audio_003", False, ["action"]), "system": "other"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            gold = root / "gold.jsonl"
            gold.write_text(
                "\n".join(
                    json.dumps(record)
                    for record in [
                        _gold_record("audio_001", "Inspect the generator shed for smoke."),
                        _gold_record("audio_002", "Inspect crops."),
                        _gold_record("audio_003", "Send one drone north."),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            jsonl_output = root / "packet.jsonl"
            markdown_output = root / "packet.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--evaluation",
                    str(evaluation),
                    "--gold-commands",
                    str(gold),
                    "--jsonl-output",
                    str(jsonl_output),
                    "--markdown-output",
                    str(markdown_output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            records = [json.loads(line) for line in jsonl_output.read_text(encoding="utf-8").splitlines()]
            markdown = markdown_output.read_text(encoding="utf-8")

        self.assertIn('"records": 1', completed.stdout)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["id"], "audio_001_span_remediation")
        self.assertEqual(records[0]["failed_intent_fields"], ["location", "target"])
        self.assertEqual(records[0]["spans"], [])
        self.assertEqual(records[0]["label_status"], "needs_human_span_review")
        self.assertIn("Do not use model output as gold labels", markdown)


def _eval_record(record_id: str, exact: bool, failed_fields: list[str]) -> dict:
    fields = ("action", "count", "location", "target", "constraints")
    return {
        "id": record_id,
        "system": "hybrid_span_parser",
        "all_fields_match": exact,
        "field_matches": {field: field not in failed_fields for field in fields},
        "actual_intent": {
            "action": "inspect",
            "count": None,
            "location": None,
            "target": "generator shed",
            "constraints": [],
        },
    }


def _gold_record(audio_id: str, text: str) -> dict:
    return {
        "id": f"{audio_id}_intent",
        "audio_id": audio_id,
        "audio_path": f"datasets/sample_audio/{audio_id}.wav",
        "text": text,
        "split": "validation",
        "expected_intent": {
            "action": "inspect",
            "count": None,
            "location": "generator shed",
            "target": "smoke",
            "constraints": [],
        },
    }


if __name__ == "__main__":
    unittest.main()
