import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compare_span_tagger_runs.py"


class CompareSpanTaggerRunsCliTests(unittest.TestCase):
    def test_cli_compares_saved_metric_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "span_nb_v0_metrics.json"
            second = root / "span_nb_v1_metrics.json"
            output = root / "comparison.json"
            first.write_text(
                json.dumps(
                    {
                        "metadata": {"model_name": "span_nb_v0", "split": "test"},
                        "summary": {"token_accuracy": 0.5, "entity_f1": 0.25, "entity_precision": 0.2, "entity_recall": 0.3},
                    }
                ),
                encoding="utf-8",
            )
            second.write_text(
                json.dumps(
                    {
                        "metadata": {"model_name": "span_nb_v1", "split": "test"},
                        "summary": {"token_accuracy": 0.75, "entity_f1": 0.5, "entity_precision": 0.45, "entity_recall": 0.55},
                    }
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--metrics",
                    str(first),
                    "--metrics",
                    str(second),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            comparison = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn('"best_by_entity_f1"', completed.stdout)
        self.assertEqual(comparison["best_by_entity_f1"], "span_nb_v1")
        self.assertEqual(comparison["runs"]["span_nb_v1"]["delta_from_first"]["entity_f1"], 0.25)


if __name__ == "__main__":
    unittest.main()
