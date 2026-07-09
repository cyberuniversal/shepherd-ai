import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations  # noqa: E402
from shepherd_ai.map_validation import render_map_validation_markdown, validate_map_locations  # noqa: E402


MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
REGION_MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_regions_v1.geojson"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_map_dataset.py"


class MapValidationTests(unittest.TestCase):
    def test_validate_map_locations_reports_roles_and_ambiguous_terms(self) -> None:
        report = validate_map_locations(load_map_locations(MAP_PATH))

        self.assertEqual(report.records, 20)
        self.assertEqual(report.role_counts["restricted_area"], 1)
        self.assertEqual(report.role_counts["obstacle"], 1)
        self.assertEqual(report.flyable_counts["false"], 2)
        ambiguous_terms = {term["term"]: term for term in report.ambiguous_terms}
        self.assertIn("road", ambiguous_terms)
        self.assertEqual(
            set(ambiguous_terms["road"]["location_ids"]),
            {"loc_service_road", "loc_main_road"},
        )
        self.assertIn("ambiguous_terms_require_clarification_before_planning", report.warnings)

    def test_markdown_report_includes_restricted_and_obstacle_records(self) -> None:
        report = validate_map_locations(load_map_locations(MAP_PATH))

        markdown = render_map_validation_markdown(report, map_path=str(MAP_PATH))

        self.assertIn("Week 3 Map Validation Report", markdown)
        self.assertIn("zone_maintenance_yard", markdown)
        self.assertIn("obs_power_lines", markdown)
        self.assertIn("not a safety certificate", markdown)

    def test_validate_map_locations_reports_polygon_geometry(self) -> None:
        report = validate_map_locations(load_map_locations(REGION_MAP_PATH))

        self.assertEqual(report.records, 3)
        self.assertEqual(report.geometry_counts["polygon"], 2)
        self.assertEqual(report.geometry_counts["circle"], 1)
        self.assertEqual(report.role_counts["restricted_area"], 1)
        self.assertEqual(report.warnings, [])

    def test_validate_map_dataset_cli_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_output = Path(tmp) / "map_report.json"
            markdown_output = Path(tmp) / "map_report.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATE_SCRIPT),
                    "--map",
                    str(MAP_PATH),
                    "--json-output",
                    str(json_output),
                    "--markdown-output",
                    str(markdown_output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(json_output.read_text(encoding="utf-8"))
            markdown = markdown_output.read_text(encoding="utf-8")

        self.assertIn("Wrote", completed.stdout)
        self.assertEqual(payload["records"], 20)
        self.assertIn("Ambiguous Terms", markdown)


if __name__ == "__main__":
    unittest.main()
