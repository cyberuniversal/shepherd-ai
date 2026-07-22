import subprocess
import sys
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/render_week8_screenshot.py"


class RenderWeek8ScreenshotCliTests(unittest.TestCase):
    def test_cli_renders_png_from_stored_simulation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "demo.png"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--simulation",
                    "outputs/evaluations/week8_roadmap_scenario_simulation.json",
                    "--telemetry",
                    "outputs/evaluations/week8_roadmap_scenario_telemetry.jsonl",
                    "--map",
                    "datasets/maps/shepherd_test_map_v1.csv",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            header = output.read_bytes()[:8]

        self.assertEqual(header, b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
