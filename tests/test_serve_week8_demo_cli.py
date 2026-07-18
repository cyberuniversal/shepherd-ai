import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/serve_week8_demo.py"


class ServeWeek8DemoCliTests(unittest.TestCase):
    def test_help_documents_local_server_controls(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("--host", completed.stdout)
        self.assertIn("--port", completed.stdout)

    def test_frontend_files_exist_and_use_threejs(self) -> None:
        html = (ROOT / "web/week8_3d/index.html").read_text(encoding="utf-8")
        app = (ROOT / "web/week8_3d/app.js").read_text(encoding="utf-8")

        self.assertIn("three@0.168.0", html)
        self.assertIn("/api/mission", app)
        self.assertIn("WebGLRenderer", app)


if __name__ == "__main__":
    unittest.main()
