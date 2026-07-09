import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_mission_flow.py"
MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"


class RenderMissionFlowCliTests(unittest.TestCase):
    def test_cli_writes_mermaid_flow_for_roadmap_scan_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "flow.md"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--command",
                    "Scan the crops in the north field.",
                    "--map",
                    str(MAP_PATH),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            markdown = output.read_text(encoding="utf-8")

        self.assertIn("steps", completed.stdout)
        self.assertIn("```mermaid", markdown)
        self.assertIn("capture_images", markdown)
        self.assertIn("run_vision_model", markdown)
        self.assertIn("return_to_launch_area", markdown)


if __name__ == "__main__":
    unittest.main()
