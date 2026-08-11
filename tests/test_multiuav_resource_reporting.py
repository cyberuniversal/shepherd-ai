import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from shepherd_ai.multiuav_resource_reporting import (
    build_resource_report_artifacts,
    load_resource_report_data,
)


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "outputs/evaluations/multiuav_resource_analysis_v1/summary.json"


class MultiUavResourceReportingTests(unittest.TestCase):
    def test_loads_only_complete_exploratory_resource_analysis(self) -> None:
        data = load_resource_report_data(ROOT)

        self.assertEqual(len(data["descriptive_rows"]), 240)
        self.assertEqual(len(data["contrast_rows"]), 96)
        self.assertEqual(
            sorted({row["repetition"] for row in data["contrast_rows"]}),
            [1, 2, 3],
        )
        self.assertTrue(data["source_scope"]["repetitions_reported_separately"])
        self.assertFalse(data["source_scope"]["repetitions_pooled"])
        self.assertFalse(data["source_scope"]["raw_model_outputs_accessed"])
        self.assertFalse(data["source_scope"]["hidden_labels_accessed"])
        self.assertEqual(
            {row["inference_status"] for row in data["contrast_rows"]},
            {"exploratory_secondary_no_confirmatory_claims"},
        )

    def test_rejects_analysis_that_invoked_models(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary_path = Path(temporary) / "summary.json"
            summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
            summary["models_invoked"] = True
            summary_path.write_text(json.dumps(summary), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "models"):
                load_resource_report_data(ROOT, summary_path=summary_path)

    def test_renders_traceable_tables_figures_and_report(self) -> None:
        data = load_resource_report_data(ROOT)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            manifest = build_resource_report_artifacts(
                repository_root=ROOT,
                report_data=data,
                figure_dir=output / "figures",
                table_dir=output / "tables",
                report_path=output / "resource_results.md",
            )

            self.assertEqual(manifest["figures"], 2)
            self.assertEqual(manifest["tables"], 2)
            self.assertEqual(manifest["reports"], 1)
            self.assertEqual(manifest["next_gate"], "manuscript_integration_pending")
            for record in manifest["outputs"]:
                path = Path(record["path"])
                self.assertGreater(path.stat().st_size, 100)
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    record["sha256"],
                )
            descriptive = (output / "tables/multiuav_resource_descriptive_v1.csv").read_text(
                encoding="utf-8"
            )
            contrasts = (output / "tables/multiuav_resource_contrasts_v1.csv").read_text(
                encoding="utf-8"
            )
            report = (output / "resource_results.md").read_text(encoding="utf-8")
            self.assertEqual(len(descriptive.splitlines()), 241)
            self.assertEqual(len(contrasts.splitlines()), 97)
            self.assertIn("secondary and exploratory", report)
            self.assertIn("reported separately", report)
            self.assertIn("not workstation, simulator, network, or UAV energy", report)


if __name__ == "__main__":
    unittest.main()
