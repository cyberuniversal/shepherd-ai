import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build_monolithic_decision_packet.py"
EVALUATE_SCRIPT = ROOT / "scripts" / "evaluate_monolithic_decision_baseline.py"


class EvaluateMonolithicDecisionBaselineCliTests(unittest.TestCase):
    def test_scores_completed_raw_predictions_without_repair(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            inputs = temp / "inputs.jsonl"
            gold = temp / "gold.jsonl"
            manifest = temp / "manifest.json"
            raw = temp / "raw.json"
            output = temp / "evaluation.json"
            report = temp / "report.md"
            subprocess.run(
                [
                    sys.executable,
                    str(BUILD_SCRIPT),
                    "--inputs-output",
                    str(inputs),
                    "--gold-output",
                    str(gold),
                    "--manifest-output",
                    str(manifest),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            input_rows = _read_jsonl(inputs)
            gold_rows = {
                row["case_id"]: row for row in _read_jsonl(gold)
            }
            raw_payload = {
                "metadata": {
                    "status": "completed",
                    "model": "test/model",
                    "model_revision": "a" * 40,
                    "model_license": "test",
                    "prompt_version": "shepherd_monolithic_decision_prompt_v1",
                    "input_sha256": hashlib.sha256(inputs.read_bytes()).hexdigest(),
                    "gold_labels_loaded": False,
                    "generation_parameters": {
                        "repetitions": 1,
                        "temperature": 0.0,
                    },
                    "device": "test T4",
                    "package_versions": {},
                },
                "records": [
                    {
                        "case_id": row["case_id"],
                        "stratum": row["stratum"],
                        "repetition": 0,
                        "seed": 17,
                        "prompt_sha256": row["prompt_sha256"],
                        "generation_elapsed_seconds": 0.1,
                        "parsed_response": {
                            "valid": True,
                            "decision": gold_rows[row["case_id"]]["expected_decision"],
                        },
                    }
                    for row in input_rows
                ],
            }
            raw.write_text(
                json.dumps(raw_payload, indent=2),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(EVALUATE_SCRIPT),
                    "--inputs",
                    str(inputs),
                    "--gold",
                    str(gold),
                    "--raw-predictions",
                    str(raw),
                    "--output",
                    str(output),
                    "--report-output",
                    str(report),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(
            payload["summary"]["monolithic_llm_majority"]["decision_accuracy"],
            1.0,
        )
        self.assertEqual(
            payload["summary"]["monolithic_llm_majority"]["invalid_predictions"],
            0,
        )
        self.assertFalse(payload["claim_limits"]["fresh_human_heldout"])


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


if __name__ == "__main__":
    unittest.main()
