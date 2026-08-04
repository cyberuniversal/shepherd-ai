from pathlib import Path
import tempfile
import unittest

from shepherd_ai.multiuav_model_cache import (
    cache_registered_snapshot,
    inventory_registered_snapshot,
    validate_external_cache_dir,
    verify_cached_snapshot,
)
from shepherd_ai.multiuav_model_revisions import REGISTERED_MODEL_REVISIONS


MODEL = REGISTERED_MODEL_REVISIONS[0]


class MultiUavModelCacheTests(unittest.TestCase):
    def test_snapshot_inventory_hashes_safetensors_and_tokenizer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = Path(temp_dir) / "cache"
            snapshot = cache / "models--qwen" / "snapshots" / MODEL.revision
            snapshot.mkdir(parents=True)
            (snapshot / "config.json").write_text("{}", encoding="utf-8")
            (snapshot / "tokenizer.json").write_text("{}", encoding="utf-8")
            (snapshot / "model.safetensors").write_bytes(b"weights")

            audit = inventory_registered_snapshot(
                model_id=MODEL.model_id,
                revision=MODEL.revision,
                cache_dir=cache,
                snapshot_dir=snapshot,
            )

            self.assertEqual(audit["weight_file_count"], 1)
            self.assertTrue(audit["all_weights_safetensors"])
            self.assertTrue(verify_cached_snapshot(audit)["valid"])

    def test_verification_rejects_changed_cached_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = Path(temp_dir) / "cache"
            snapshot = cache / "models--qwen" / "snapshots" / MODEL.revision
            snapshot.mkdir(parents=True)
            (snapshot / "config.json").write_text("{}", encoding="utf-8")
            (snapshot / "tokenizer.json").write_text("{}", encoding="utf-8")
            weights = snapshot / "model.safetensors"
            weights.write_bytes(b"weights")
            audit = inventory_registered_snapshot(
                model_id=MODEL.model_id,
                revision=MODEL.revision,
                cache_dir=cache,
                snapshot_dir=snapshot,
            )
            weights.write_bytes(b"changed")

            with self.assertRaisesRegex(ValueError, "differs from recorded"):
                verify_cached_snapshot(audit)

    def test_cache_download_is_pinned_and_external(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repository"
            root.mkdir()
            cache = Path(temp_dir) / "cache"
            snapshot = cache / "models--qwen" / "snapshots" / MODEL.revision
            snapshot.mkdir(parents=True)
            (snapshot / "config.json").write_text("{}", encoding="utf-8")
            (snapshot / "tokenizer.json").write_text("{}", encoding="utf-8")
            (snapshot / "model.safetensors").write_bytes(b"weights")
            calls = []

            def fake_download(**kwargs):
                calls.append(kwargs)
                return str(snapshot)

            audit = cache_registered_snapshot(
                model_id=MODEL.model_id,
                revision=MODEL.revision,
                cache_dir=cache,
                repository_root=root,
                snapshot_download=fake_download,
            )

            self.assertEqual(audit["revision"], MODEL.revision)
            self.assertEqual(calls[0]["revision"], MODEL.revision)
            self.assertFalse(calls[0]["local_files_only"])

    def test_repository_cache_and_unregistered_revision_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repository"
            root.mkdir()
            with self.assertRaisesRegex(ValueError, "outside the repository"):
                validate_external_cache_dir(root / "models", root)
            with self.assertRaisesRegex(ValueError, "frozen registry"):
                inventory_registered_snapshot(
                    model_id=MODEL.model_id,
                    revision="0" * 40,
                    cache_dir=Path(temp_dir),
                    snapshot_dir=Path(temp_dir),
                )


if __name__ == "__main__":
    unittest.main()
