import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_vision_manifest.py"


class ValidateVisionManifestCliTests(unittest.TestCase):
    def test_cli_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "datasets" / "aerial_images" / "sample.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"not-a-real-image-for-manifest-test")
            manifest = root / "datasets" / "aerial_images" / "manifest.jsonl"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "aerial_001",
                        "image_path": "datasets/aerial_images/sample.png",
                        "split": "demo",
                        "source": "unit_test_fixture",
                        "data_type": "synthetic_manifest_fixture",
                        "license": "test_fixture_not_for_research",
                        "provenance_url": "local_test_fixture",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            output = root / "summary.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--manifest",
                    str(manifest),
                    "--dataset-root",
                    str(root),
                    "--summary-output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn('"records": 1', completed.stdout)
        self.assertEqual(payload["summary"]["records"], 1)
        self.assertIn("not detection-performance evidence", payload["metadata"]["research_note"])


if __name__ == "__main__":
    unittest.main()
