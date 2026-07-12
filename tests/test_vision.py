import json
from pathlib import Path
import tempfile
import unittest

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.vision import (  # noqa: E402
    DetectionRecord,
    VisionManifestError,
    load_vision_manifest,
    require_cuda_device,
    summarize_detections,
    summarize_vision_manifest,
    sha256_file,
)


class VisionManifestTests(unittest.TestCase):
    def test_loads_manifest_with_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "datasets" / "aerial_images" / "sample.jpg"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"not-a-real-image-for-manifest-test")
            manifest = root / "datasets" / "aerial_images" / "manifest.jsonl"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "aerial_001",
                        "image_path": "datasets/aerial_images/sample.jpg",
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

            records = load_vision_manifest(manifest, dataset_root=root)
            summary = summarize_vision_manifest(records)

        self.assertEqual(records[0].id, "aerial_001")
        self.assertEqual(summary["records"], 1)
        self.assertEqual(summary["split_counts"], {"demo": 1})
        self.assertEqual(summary["license_counts"], {"test_fixture_not_for_research": 1})

    def test_rejects_missing_license(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "image.jpg"
            image.write_bytes(b"test")
            manifest = root / "manifest.jsonl"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "aerial_001",
                        "image_path": "image.jpg",
                        "split": "demo",
                        "source": "unit_test_fixture",
                        "data_type": "synthetic_manifest_fixture",
                        "provenance_url": "local_test_fixture",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(VisionManifestError, "missing required fields: license"):
                load_vision_manifest(manifest, dataset_root=root)

    def test_rejects_path_outside_dataset_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            outside = Path(tmp) / "outside.jpg"
            outside.write_bytes(b"test")
            manifest = root / "manifest.jsonl"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "aerial_001",
                        "image_path": "../outside.jpg",
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

            with self.assertRaisesRegex(VisionManifestError, "must stay within dataset_root"):
                load_vision_manifest(manifest, dataset_root=root)

    def test_summarizes_detection_counts_without_performance_claims(self) -> None:
        summary = summarize_detections(
            [
                DetectionRecord(
                    image_id="aerial_001",
                    image_path="datasets/aerial_images/sample.jpg",
                    model_name="yolov8n.pt",
                    model_version="test",
                    class_id=0,
                    class_name="person",
                    confidence=0.9,
                    bbox_xyxy=(1.0, 2.0, 3.0, 4.0),
                )
            ],
            image_count=1,
        )

        self.assertEqual(summary["detections"], 1)
        self.assertEqual(summary["class_counts"], {"person": 1})
        self.assertIn("not mAP", summary["evaluation_note"])

    def test_validates_declared_image_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "sample.jpg"
            image.write_bytes(b"research-image-fixture")
            expected_sha256 = sha256_file(image)
            manifest = root / "manifest.jsonl"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "aerial_001",
                        "image_path": "sample.jpg",
                        "split": "validation",
                        "source": "unit_test_fixture",
                        "data_type": "synthetic_manifest_fixture",
                        "license": "test_fixture_not_for_research",
                        "provenance_url": "local_test_fixture",
                        "sha256": expected_sha256,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            records = load_vision_manifest(manifest, dataset_root=root)

        self.assertEqual(records[0].sha256, expected_sha256)

    def test_rejects_checksum_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "sample.jpg"
            image.write_bytes(b"research-image-fixture")
            manifest = root / "manifest.jsonl"
            manifest.write_text(
                json.dumps(
                    {
                        "id": "aerial_001",
                        "image_path": "sample.jpg",
                        "split": "validation",
                        "source": "unit_test_fixture",
                        "data_type": "synthetic_manifest_fixture",
                        "license": "test_fixture_not_for_research",
                        "provenance_url": "local_test_fixture",
                        "sha256": "0" * 64,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(VisionManifestError, "sha256 mismatch"):
                load_vision_manifest(manifest, dataset_root=root)

    def test_requires_named_cuda_device(self) -> None:
        class FakeCuda:
            @staticmethod
            def is_available() -> bool:
                return True

            @staticmethod
            def device_count() -> int:
                return 1

            @staticmethod
            def get_device_name(index: int) -> str:
                self.assertEqual(index, 0)
                return "Tesla T4"

        class FakeTorch:
            cuda = FakeCuda()

        metadata = require_cuda_device("T4", FakeTorch())

        self.assertEqual(metadata["cuda_device_names"], ["Tesla T4"])

    def test_rejects_cpu_when_cuda_is_required(self) -> None:
        class FakeCuda:
            @staticmethod
            def is_available() -> bool:
                return False

            @staticmethod
            def device_count() -> int:
                return 0

        class FakeTorch:
            cuda = FakeCuda()

        with self.assertRaisesRegex(RuntimeError, "required CUDA device"):
            require_cuda_device("T4", FakeTorch())


if __name__ == "__main__":
    unittest.main()
