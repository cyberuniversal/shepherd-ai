from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import ground_intent, load_map_locations  # noqa: E402
from shepherd_ai.intent import parse_intent  # noqa: E402
from shepherd_ai.map_visualization import render_map  # noqa: E402


MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
REGION_MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_regions_v1.geojson"
RENDER_SCRIPT = ROOT / "scripts" / "render_grounding_map.py"


class MapVisualizationTests(unittest.TestCase):
    def test_render_map_writes_html_with_grounded_location(self) -> None:
        locations = load_map_locations(MAP_PATH)
        grounded = ground_intent(parse_intent("Inspect the greenhouse."), locations)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "map.html"
            render_map(locations, output, grounded_intent=grounded)
            html = output.read_text(encoding="utf-8")

        self.assertIn("Shepherd-AI Grounding Map", html)
        self.assertIn("loc_greenhouse", html)
        self.assertIn("requires_clearance", html)
        self.assertIn("Grounding Summary", html)

    def test_render_map_writes_html_with_polygon_location(self) -> None:
        locations = load_map_locations(REGION_MAP_PATH)
        grounded = ground_intent(parse_intent("Inspect the polygon zone."), locations)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "map.html"
            render_map(locations, output, grounded_intent=grounded)
            html = output.read_text(encoding="utf-8")

        self.assertIn("poly_north_field", html)
        self.assertIn("polygon", html)
        self.assertIn("L.polygon", html)

    def test_render_grounding_map_cli_writes_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "map.html"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(RENDER_SCRIPT),
                    "--map",
                    str(MAP_PATH),
                    "--command",
                    "Send two drones north and inspect the crops.",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            html = output.read_text(encoding="utf-8")

        self.assertIn("Wrote", completed.stdout)
        self.assertIn("loc_north_field", html)


if __name__ == "__main__":
    unittest.main()
