import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analyze_hf_transcript_intent_errors.py"


class AnalyzeHfTranscriptIntentErrorsCliTests(unittest.TestCase):
    def test_cli_separates_human_errors_from_asr_added_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            human_eval = root / "human.json"
            asr_eval = root / "asr.json"
            human_eval.write_text(
                json.dumps(
                    {
                        "records": [
                            _record("audio_001", "hybrid_span_parser", True, []),
                            _record("audio_002", "hybrid_span_parser", False, ["target"]),
                        ]
                    }
                ),
                encoding="utf-8",
            )
            asr_eval.write_text(
                json.dumps(
                    {
                        "records": [
                            _record("audio_001", "hybrid_span_parser", False, ["location"]),
                            _record("audio_002", "hybrid_span_parser", False, ["target"]),
                        ]
                    }
                ),
                encoding="utf-8",
            )
            json_output = root / "analysis.json"
            md_output = root / "analysis.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--human-evaluation",
                    str(human_eval),
                    "--asr-evaluation",
                    str(asr_eval),
                    "--json-output",
                    str(json_output),
                    "--markdown-output",
                    str(md_output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            analysis = json.loads(json_output.read_text(encoding="utf-8"))
            markdown = md_output.read_text(encoding="utf-8")

        self.assertIn("asr_added_failure_records", completed.stdout)
        summary = analysis["summary"]["hybrid_span_parser"]
        self.assertEqual(summary["human_error_records"], 1)
        self.assertEqual(summary["asr_error_records"], 2)
        self.assertEqual(summary["asr_added_failure_records"], 1)
        self.assertEqual(
            analysis["systems"]["hybrid_span_parser"]["asr_added_failures"]["examples"][0]["id"],
            "audio_001",
        )
        self.assertIn("ASR-added failures", markdown)


def _record(record_id: str, system: str, exact: bool, failed_fields: list[str]) -> dict:
    fields = ("action", "count", "location", "target", "constraints")
    return {
        "id": record_id,
        "system": system,
        "transcript": f"Transcript for {record_id}",
        "all_fields_match": exact,
        "field_matches": {field: field not in failed_fields for field in fields},
        "expected_intent": {},
        "actual_intent": {},
    }


if __name__ == "__main__":
    unittest.main()
