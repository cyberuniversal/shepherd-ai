import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "inspect_agriculture_vision_layout.py"


class InspectAgricultureVisionLayoutCliTests(unittest.TestCase):
    def test_records_structure_and_label_like_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "dataset"
            rgb = root / "field_images" / "rgb"
            labels = root / "field_labels" / "double_plant"
            masks = root / "field_bounds"
            rgb.mkdir(parents=True)
            labels.mkdir(parents=True)
            masks.mkdir(parents=True)
            (rgb / "FIELD_0.jpg").write_bytes(b"rgb")
            (labels / "FIELD_0.png").write_bytes(b"label")
            (masks / "FIELD_0.png").write_bytes(b"mask")
            output = Path(tmp) / "layout.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--dataset-dir",
                    str(root),
                    "--output",
                    str(output),
                    "--sample-limit",
                    "2",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn('"files": 3', completed.stdout)
        self.assertEqual(payload["summary"]["files"], 3)
        self.assertEqual(payload["summary"]["extension_counts"], {".jpg": 1, ".png": 2})
        self.assertEqual(
            payload["label_like_directories"],
            ["field_bounds", "field_labels", "field_labels/double_plant"],
        )
        self.assertEqual(len(payload["sample_files"]), 2)
        self.assertNotIn(str(root), json.dumps(payload))

    def test_rejects_missing_dataset_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--dataset-dir",
                    str(Path(tmp) / "missing"),
                    "--output",
                    str(Path(tmp) / "layout.json"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("does not exist", completed.stderr)

    def test_rejects_empty_dataset_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--dataset-dir",
                    tmp,
                    "--output",
                    str(Path(tmp) / "layout.json"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("contains no files", completed.stderr)


if __name__ == "__main__":
    unittest.main()
