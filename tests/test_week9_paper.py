import copy
import json
from pathlib import Path
import tempfile
import unittest

from shepherd_ai.week9_paper import (
    REQUIRED_METRICS,
    load_week9_paper_evidence,
    render_csv,
    render_traceability_markdown,
)


ROOT = Path(__file__).resolve().parents[1]


class Week9PaperEvidenceTests(unittest.TestCase):
    def test_registered_evidence_preserves_all_metrics_and_weak_vision_result(self) -> None:
        evidence = load_week9_paper_evidence(ROOT)
        rows = {row["metric"]: row for row in evidence["metric_rows"]}

        self.assertEqual(tuple(rows), REQUIRED_METRICS)
        self.assertAlmostEqual(rows["detection_performance"]["value"], 0.023561720474907635)
        self.assertEqual(rows["detection_performance"]["denominator"], 6)
        self.assertFalse(evidence["claim_limits"]["novelty_claimed"])

    def test_incomplete_audit_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._fixture_root(Path(temporary))
            audit_path = root / "outputs/evaluations/week8_completion_gate_audit.json"
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            audit["completion_allowed"] = False
            audit["blockers"] = ["missing_evidence"]
            audit_path.write_text(json.dumps(audit), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "does not permit"):
                load_week9_paper_evidence(root)

    def test_unsupported_novelty_claim_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._fixture_root(Path(temporary))
            evaluation_path = root / "outputs/evaluations/week8_end_to_end_evaluation.json"
            evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
            evaluation["novelty_claimed"] = True
            evaluation_path.write_text(json.dumps(evaluation), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "novelty_claimed"):
                load_week9_paper_evidence(root)

    def test_renderers_include_sources_and_claim_limits(self) -> None:
        evidence = load_week9_paper_evidence(ROOT)
        csv_text = render_csv(
            evidence["metric_rows"],
            ("metric", "value", "denominator", "unit", "definition", "source_artifact"),
        )
        report = render_traceability_markdown(evidence)

        self.assertIn("detection_performance,0.023561720474907635", csv_text)
        self.assertIn("week8_mission_vision_evaluation.json", report)
        self.assertIn("`novelty_claimed`: `false`", report)

    def _fixture_root(self, root: Path) -> Path:
        output = root / "outputs/evaluations"
        output.mkdir(parents=True)
        source_evaluation = ROOT / "outputs/evaluations/week8_end_to_end_evaluation.json"
        evaluation = copy.deepcopy(json.loads(source_evaluation.read_text(encoding="utf-8")))
        for metric in evaluation["metrics"].values():
            source = metric.get("source_artifact")
            if source:
                source_path = root / source
                source_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.write_text("{}", encoding="utf-8")
        (output / "week8_end_to_end_evaluation.json").write_text(
            json.dumps(evaluation), encoding="utf-8"
        )
        audit = json.loads(
            (ROOT / "outputs/evaluations/week8_completion_gate_audit.json").read_text(
                encoding="utf-8"
            )
        )
        (output / "week8_completion_gate_audit.json").write_text(
            json.dumps(audit), encoding="utf-8"
        )
        return root


if __name__ == "__main__":
    unittest.main()
