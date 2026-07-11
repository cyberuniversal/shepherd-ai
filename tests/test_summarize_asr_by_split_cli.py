import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "summarize_asr_by_split.py"


class SummarizeAsrBySplitCliTests(unittest.TestCase):
    def test_cli_writes_split_level_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio_dir = root / "datasets" / "sample_audio"
            audio_dir.mkdir(parents=True)
            for audio_id in ("audio_001", "audio_002"):
                (audio_dir / f"{audio_id}.wav").write_bytes(b"RIFF")

            manifest = audio_dir / "manifest.jsonl"
            manifest.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "id": "audio_001",
                                "audio_path": "datasets/sample_audio/audio_001.wav",
                                "transcript": "Return all drones.",
                                "source": "test",
                                "data_type": "human_recorded_audio",
                                "split": "train",
                            }
                        ),
                        json.dumps(
                            {
                                "id": "audio_002",
                                "audio_path": "datasets/sample_audio/audio_002.wav",
                                "transcript": "Send two drones west.",
                                "source": "test",
                                "data_type": "human_recorded_audio",
                                "split": "test",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            evaluation = root / "evaluation.json"
            evaluation.write_text(
                json.dumps(
                    {
                        "metadata": {"model_name": "whisper", "model_version": "base"},
                        "summary": {"records": 2, "mean_word_error_rate": 0.125},
                        "records": [
                            {
                                "id": "audio_001",
                                "expected": "Return all drones.",
                                "predicted": "Return all drones.",
                                "word_error_rate": 0.0,
                                "exact_match": True,
                            },
                            {
                                "id": "audio_002",
                                "expected": "Send two drones west.",
                                "predicted": "Send drones west.",
                                "word_error_rate": 0.25,
                                "exact_match": False,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "split_summary.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--manifest",
                    str(manifest),
                    "--dataset-root",
                    str(root),
                    "--evaluation",
                    str(evaluation),
                    "--output",
                    str(output),
                    "--split-policy",
                    "test policy",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            summary = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn('"test"', completed.stdout)
        self.assertEqual(summary["metadata"]["split_policy"], "test policy")
        self.assertEqual(summary["split_summaries"]["train"]["exact_match_accuracy"], 1.0)
        self.assertEqual(summary["split_summaries"]["test"]["mean_word_error_rate"], 0.25)


if __name__ == "__main__":
    unittest.main()
