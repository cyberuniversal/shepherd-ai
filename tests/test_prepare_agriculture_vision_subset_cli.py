import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image


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

    def test_train_label_stratified_selection_reserves_rare_positive_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "agriculture-vision"
            rgb = dataset / "train" / "images" / "rgb"
            labels = dataset / "labels" / "field_labels"
            rgb.mkdir(parents=True)
            for index in range(8):
                (rgb / f"field_{index:02d}.jpg").write_bytes(str(index).encode("ascii"))
            for class_name, indices in {"endrow": (6,), "water": (7,)}.items():
                class_dir = labels / class_name
                class_dir.mkdir(parents=True)
                for index in indices:
                    Image.new("L", (2, 2), color=255).save(class_dir / f"field_{index:02d}.png")
            output = root / "manifest.jsonl"

            completed = subprocess.run(
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
                    "train-label-stratified",
                    "--selection-seed",
                    "17",
                    "--labels-dir",
                    str(dataset / "labels"),
                    "--min-positive-records-per-class",
                    "1",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            summary = json.loads(completed.stdout)

        selected_ids = {row["id"] for row in rows}
        self.assertIn("agriculture_vision_train_field_06", selected_ids)
        self.assertIn("agriculture_vision_train_field_07", selected_ids)
        self.assertEqual(summary["selected_train_positive_records"]["endrow"], 1)
        self.assertEqual(summary["selected_train_positive_records"]["water"], 1)
        self.assertEqual(len(summary["split_id_sha256"]["train"]), 64)

    def test_train_label_presence_cache_reproduces_selection_without_mask_reads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "agriculture-vision"
            rgb = dataset / "train" / "images" / "rgb"
            labels = dataset / "labels" / "field_labels" / "water"
            rgb.mkdir(parents=True)
            labels.mkdir(parents=True)
            for index in range(6):
                (rgb / f"field_{index:02d}.jpg").write_bytes(str(index).encode("ascii"))
            Image.new("L", (2, 2), color=255).save(labels / "field_05.png")
            cache = root / "presence.json"
            outputs = []

            for run in range(2):
                output = root / f"manifest_{run}.jsonl"
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
                        "3",
                        "--selection-strategy",
                        "train-label-stratified",
                        "--labels-dir",
                        str(dataset / "labels"),
                        "--label-presence-cache",
                        str(cache),
                    ],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                outputs.append(output.read_text(encoding="utf-8"))
                if run == 0:
                    shutil.rmtree(dataset / "labels")

        self.assertEqual(outputs[0], outputs[1])

    def test_train_label_presence_cache_rejects_candidate_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "agriculture-vision"
            rgb = dataset / "train" / "images" / "rgb"
            rgb.mkdir(parents=True)
            (rgb / "field_00.jpg").write_bytes(b"rgb")
            cache = root / "presence.json"
            cache.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "class_names": [
                            "double_plant",
                            "drydown",
                            "endrow",
                            "nutrient_deficiency",
                            "planter_skip",
                            "storm_damage",
                            "water",
                            "waterway",
                            "weed_cluster",
                        ],
                        "positive_classes_by_image_id": {"wrong_id": []},
                    }
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--dataset-dir",
                    str(dataset),
                    "--dataset-root",
                    str(root),
                    "--output",
                    str(root / "manifest.jsonl"),
                    "--accept-terms",
                    "--selection-strategy",
                    "train-label-stratified",
                    "--labels-dir",
                    str(dataset / "labels"),
                    "--label-presence-cache",
                    str(cache),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("candidate image IDs", completed.stderr)


if __name__ == "__main__":
    unittest.main()
