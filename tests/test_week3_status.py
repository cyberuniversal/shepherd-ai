import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week3_status import (  # noqa: E402
    build_week3_grounding_status,
    render_week3_grounding_status_markdown,
)


STATUS_SCRIPT = ROOT / "scripts" / "summarize_week3_grounding_status.py"


class Week3StatusTests(unittest.TestCase):
    def test_build_week3_grounding_status_marks_synthetic_handoff_ready(self) -> None:
        status = build_week3_grounding_status(
            map_validation={
                "records": 20,
                "ambiguous_terms": [{"term": "road"}],
                "restricted_records": [{"id": "zone_maintenance_yard"}],
                "obstacle_records": [{"id": "obs_power_lines"}],
                "warnings": ["ambiguous_terms_require_clarification_before_planning"],
            },
            grounding_evaluations=[
                {
                    "metadata": {"dataset": "grounding_examples_v1.jsonl"},
                    "summary": {
                        "records": 1,
                        "exact_record_matches": 1,
                        "reference_matches": 2,
                        "total_references": 2,
                    },
                    "records": [{"ready_for_planning": True}],
                }
            ],
            clarification_reports=[
                {"metadata": {"map": "map.csv"}, "clarification_report": {"requests": [{}], "blocks_planning": True}}
            ],
            applied_resolutions=[
                {
                    "metadata": {"source_grounded_json": "clarification.json"},
                    "operator_choices": {"location": "loc_service_road"},
                    "clarification_report": {"requests": [], "blocks_planning": False, "ready_for_planning": True},
                }
            ],
        )

        payload = status.to_dict()

        self.assertTrue(payload["readiness"]["development_handoff_ready"])
        self.assertTrue(payload["readiness"]["not_real_world_benchmark"])
        self.assertEqual(payload["map_validation"]["warnings"], 1)

    def test_markdown_status_preserves_limitations(self) -> None:
        status = build_week3_grounding_status(
            map_validation={"records": 1, "ambiguous_terms": [], "restricted_records": [], "obstacle_records": [], "warnings": []},
            grounding_evaluations=[],
            clarification_reports=[],
            applied_resolutions=[],
        )

        markdown = render_week3_grounding_status_markdown(status)

        self.assertIn("not a real-world grounding benchmark", markdown)
        self.assertIn("Operator-applied clarifications", markdown)

    def test_status_cli_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            map_validation = root / "map_validation.json"
            evaluation = root / "evaluation.json"
            clarification = root / "clarification.json"
            resolution = root / "resolution.json"
            output_json = root / "status.json"
            output_markdown = root / "status.md"

            map_validation.write_text(
                json.dumps({"records": 1, "ambiguous_terms": [], "restricted_records": [], "obstacle_records": [], "warnings": []}),
                encoding="utf-8",
            )
            evaluation.write_text(
                json.dumps(
                    {
                        "metadata": {"dataset": "eval.jsonl"},
                        "summary": {"records": 1, "exact_record_matches": 1, "reference_matches": 2, "total_references": 2},
                        "records": [{"ready_for_planning": True}],
                    }
                ),
                encoding="utf-8",
            )
            clarification.write_text(
                json.dumps({"metadata": {"map": "map.csv"}, "clarification_report": {"requests": [{}], "blocks_planning": True}}),
                encoding="utf-8",
            )
            resolution.write_text(
                json.dumps(
                    {
                        "metadata": {"source_grounded_json": "clarification.json"},
                        "operator_choices": {"location": "loc_service_road"},
                        "clarification_report": {"requests": [], "blocks_planning": False, "ready_for_planning": True},
                    }
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(STATUS_SCRIPT),
                    "--map-validation",
                    str(map_validation),
                    "--grounding-evaluation",
                    str(evaluation),
                    "--clarification-report",
                    str(clarification),
                    "--applied-resolution",
                    str(resolution),
                    "--output-json",
                    str(output_json),
                    "--output-markdown",
                    str(output_markdown),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output_json.read_text(encoding="utf-8"))
            markdown = output_markdown.read_text(encoding="utf-8")

        self.assertIn("development_handoff_ready", completed.stdout)
        self.assertTrue(payload["readiness"]["development_handoff_ready"])
        self.assertIn("Week 3 Grounding Status", markdown)


if __name__ == "__main__":
    unittest.main()
