import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from shepherd_ai.multiuav_study_figures import (
    build_accuracy_figure_artifacts,
    load_accuracy_figure_data,
)


ROOT = Path(__file__).resolve().parents[1]
SCORING_SUMMARY = ROOT / "outputs/evaluations/multiuav_accuracy_scoring_v1/summary.json"
BOOTSTRAP_SUMMARY = ROOT / "outputs/evaluations/multiuav_accuracy_bootstrap_v1/summary.json"


class MultiUavStudyFigureTests(unittest.TestCase):
    def test_loads_only_registered_accuracy_outcomes(self) -> None:
        data = load_accuracy_figure_data(ROOT)

        self.assertEqual(len(data["primary_rate_rows"]), 16)
        self.assertEqual(len(data["registered_contrast_rows"]), 8)
        self.assertFalse(data["source_scope"]["raw_model_outputs_accessed"])
        self.assertFalse(data["source_scope"]["smoke_rows_included"])
        self.assertFalse(data["source_scope"]["resource_rows_included"])
        result = next(
            row
            for row in data["registered_contrast_rows"]
            if row["model_label"] == "Qwen2.5-7B"
            and row["contrast_role"] == "primary_contrast"
            and row["outcome"] == "end_to_end_case_success_rate"
        )
        self.assertAlmostEqual(result["point_estimate"], 0.16056338028169015)
        self.assertAlmostEqual(result["ci_lower"], 0.1507042253521127)
        self.assertAlmostEqual(result["ci_upper"], 0.16971830985915495)

    def test_rejects_bootstrap_bound_to_different_scoring_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            scoring_path = Path(temporary) / "scoring.json"
            scoring = json.loads(SCORING_SUMMARY.read_text(encoding="utf-8"))
            scoring["claim_status"] = "mutated"
            scoring_path.write_text(json.dumps(scoring), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                load_accuracy_figure_data(
                    ROOT,
                    scoring_summary_path=scoring_path,
                    bootstrap_summary_path=BOOTSTRAP_SUMMARY,
                )

    def test_rejects_resource_results_in_accuracy_figure_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bootstrap_path = Path(temporary) / "bootstrap.json"
            bootstrap = copy.deepcopy(
                json.loads(BOOTSTRAP_SUMMARY.read_text(encoding="utf-8"))
            )
            bootstrap["resource_analysis_included"] = True
            bootstrap_path.write_text(json.dumps(bootstrap), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Resource|resource"):
                load_accuracy_figure_data(
                    ROOT,
                    scoring_summary_path=SCORING_SUMMARY,
                    bootstrap_summary_path=bootstrap_path,
                )

    def test_renders_nonblank_figures_and_traceable_tables(self) -> None:
        data = load_accuracy_figure_data(ROOT)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            manifest = build_accuracy_figure_artifacts(
                repository_root=ROOT,
                figure_data=data,
                figure_dir=output / "figures",
                table_dir=output / "tables",
            )

            self.assertEqual(manifest["figures"], 2)
            self.assertEqual(manifest["tables"], 2)
            paths = {Path(item["path"]) for item in manifest["outputs"]}
            pngs = [path for path in paths if path.suffix == ".png"]
            pdfs = [path for path in paths if path.suffix == ".pdf"]
            self.assertEqual(len(pngs), 2)
            self.assertEqual(len(pdfs), 2)
            for record in manifest["outputs"]:
                path = Path(record["path"])
                self.assertGreater(path.stat().st_size, 500)
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    record["sha256"],
                )
            primary_csv = (output / "tables/multiuav_accuracy_primary_rates_v1.csv").read_text(
                encoding="utf-8"
            )
            contrasts_csv = (
                output / "tables/multiuav_accuracy_registered_contrasts_v1.csv"
            ).read_text(encoding="utf-8")
            self.assertEqual(len(primary_csv.splitlines()), 17)
            self.assertEqual(len(contrasts_csv.splitlines()), 9)
            self.assertIn("Qwen2.5-7B", contrasts_csv)


if __name__ == "__main__":
    unittest.main()
