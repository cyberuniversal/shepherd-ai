import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_agriculture_vision_subset.py"


class PrepareAgricultureVisionSubsetCliTests(unittest.TestCase):
    def test_requires_explicit_terms_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--dataset-dir",
                    tmp,
                    "--dataset-root",
                    tmp,
                    "--output",
                    str(Path(tmp) / "manifest.jsonl"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("--accept-terms", completed.stderr)

    def test_builds_deterministic_split_preserving_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "agriculture-vision"
            for split in ("train", "val", "test"):
                rgb = dataset / split / "images" / "rgb"
                rgb.mkdir(parents=True)
                (rgb / f"field_{split}.jpg").write_bytes(split.encode("ascii"))
            output = root / "manifest.jsonl"

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--dataset-dir",
                    str(dataset),
                    "--dataset-root",
                    str(root),
                    "--output",
                    str(output),
                    "--accept-terms",
                    "--max-per-split",
                    "1",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

        self.assertEqual([row["split"] for row in rows], ["test", "train", "validation"])
        self.assertTrue(all(len(row["sha256"]) == 64 for row in rows))
        self.assertTrue(all(row["data_type"] == "public_human_annotated_aerial_imagery" for row in rows))
        self.assertTrue(all("non-commercial" in row["license"].lower() for row in rows))

    def test_uses_official_farmland_split_json_without_directory_splits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "agriculture-vision"
            rgb = dataset / "images" / "rgb"
            rgb.mkdir(parents=True)
            for field_id in ("FIELDTRAIN", "FIELDVAL", "FIELDTEST"):
                (rgb / f"{field_id}_0-0-512-512.jpg").write_bytes(field_id.encode("ascii"))
            split_json = dataset / "data2017_splits.json"
            split_json.write_text(
                json.dumps(
                    {
                        "train": ["FIELDTRAIN"],
                        "val": ["FIELDVAL"],
                        "test": ["FIELDTEST"],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "manifest.jsonl"

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--dataset-dir",
                    str(dataset),
                    "--dataset-root",
                    str(root),
                    "--split-json",
                    str(split_json),
                    "--output",
                    str(output),
                    "--accept-terms",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

        self.assertEqual([row["split"] for row in rows], ["test", "train", "validation"])

    def test_seeded_hash_selection_is_reproducible_and_not_sorted_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "agriculture-vision"
            rgb = dataset / "train" / "images" / "rgb"
            rgb.mkdir(parents=True)
            for index in range(12):
                (rgb / f"field_{index:02d}.jpg").write_bytes(str(index).encode("ascii"))

            selected_ids = []
            for output_name in ("first.jsonl", "second.jsonl"):
                output = root / output_name
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--dataset-dir",
                        str(dataset),
                        "--dataset-root",
                        str(root),
                        "--output",
                        str(output),
                        "--accept-terms",
                        "--max-per-split",
                        "4",
                        "--selection-strategy",
                        "seeded-hash",
                        "--selection-seed",
                        "17",
                    ],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                selected_ids.append(
                    [json.loads(line)["id"] for line in output.read_text(encoding="utf-8").splitlines()]
                )

        self.assertEqual(selected_ids[0], selected_ids[1])
        self.assertNotEqual(
            selected_ids[0],
            [f"agriculture_vision_train_field_{index:02d}" for index in range(4)],
        )


if __name__ == "__main__":
    unittest.main()
