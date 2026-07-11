from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations  # noqa: E402
from shepherd_ai.grounding_coverage import (  # noqa: E402
    build_grounding_coverage_report,
    render_grounding_coverage_markdown,
)
from shepherd_ai.grounding_dataset import load_grounding_dataset  # noqa: E402


MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
HOLDOUT_PATH = ROOT / "datasets" / "maps" / "grounding_holdout_synthetic_v1.jsonl"


class GroundingCoverageTests(unittest.TestCase):
    def test_build_grounding_coverage_report_separates_covered_and_untested_records(self) -> None:
        locations = load_map_locations(MAP_PATH)
        records = load_grounding_dataset(HOLDOUT_PATH, locations)

        report = build_grounding_coverage_report(locations, [records])
        payload = report.to_dict()

        self.assertEqual(payload["map_records"], 20)
        self.assertIn("loc_greenhouse", payload["covered_location_ids"])
        self.assertIn("loc_irrigation_canal", payload["untested_location_ids"])
        self.assertEqual(payload["role_coverage"]["obstacle"]["covered"], 1)
        self.assertIn("map_records_without_grounding_coverage", payload["warnings"])

    def test_render_grounding_coverage_markdown_preserves_limitations(self) -> None:
        locations = load_map_locations(MAP_PATH)
        records = load_grounding_dataset(HOLDOUT_PATH, locations)
        report = build_grounding_coverage_report(locations, [records])

        markdown = render_grounding_coverage_markdown(report, map_path=str(MAP_PATH))

        self.assertIn("Week 3 Grounding Coverage Report", markdown)
        self.assertIn("not real-world grounding accuracy", markdown)
        self.assertIn("Untested Location IDs", markdown)


if __name__ == "__main__":
    unittest.main()
