import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_agriculture_vision_labels.py"
CLASSES = (
    "double_plant",
    "drydown",
    "endrow",
    "nutrient_deficiency",
    "planter_skip",
    "storm_damage",
    "water",
    "waterway",
    "weed_cluster",
)


class ValidateAgricultureVisionLabelsCliTests(unittest.TestCase):
    def test_audits_requested_splits_without_reading_test(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            labels = root / "labels"
            manifest = root / "manifest.jsonl"
            rows = []
            for split in ("train", "validation", "test"):
                stem = f"FIELD_{split}"
                image = root / f"{stem}.jpg"
                image.write_bytes(b"fixture")
                rows.append(self._manifest_row(stem, image.name, split))
                self._write_masks(labels, stem, positive=split != "test")
            manifest.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            output = root / "summary.json"

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--manifest",
                    str(manifest),
                    "--dataset-root",
                    str(root),
                    "--labels-dir",
                    str(labels),
                    "--split",
                    "train",
                    "--split",
                    "validation",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["records"], 2)
        self.assertEqual(payload["split_counts"], {"train": 1, "validation": 1})
        self.assertEqual(payload["valid_pixels"], 8)
        self.assertEqual(payload["positive_pixels"]["double_plant"], 2)
        self.assertEqual(payload["overlap_pixels"], 2)
        self.assertEqual(payload["excluded_splits"], ["test"])

    def test_rejects_test_split_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--manifest",
                    str(Path(tmp) / "missing.jsonl"),
                    "--dataset-root",
                    tmp,
                    "--labels-dir",
                    tmp,
                    "--split",
                    "test",
                    "--output",
                    str(Path(tmp) / "summary.json"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("limited to train/validation", completed.stderr)

    @staticmethod
    def _manifest_row(stem: str, image_path: str, split: str) -> dict[str, str]:
        return {
            "id": stem,
            "image_path": image_path,
            "split": split,
            "source": "fixture",
            "data_type": "synthetic_fixture",
            "license": "fixture",
            "provenance_url": "fixture",
        }

    @staticmethod
    def _write_masks(root: Path, stem: str, *, positive: bool) -> None:
        values = np.full((2, 2), 255, dtype=np.uint8)
        for directory in ("field_bounds", "field_masks"):
            path = root / directory / f"{stem}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(values).save(path)
        for class_name in CLASSES:
            mask = np.zeros((2, 2), dtype=np.uint8)
            if positive and class_name in {"double_plant", "waterway"}:
                mask[0, 0] = 255
            path = root / "field_labels" / class_name / f"{stem}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(mask).save(path)


if __name__ == "__main__":
    unittest.main()
