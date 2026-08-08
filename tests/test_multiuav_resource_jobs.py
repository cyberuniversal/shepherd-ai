from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class MultiUavResourceJobTests(unittest.TestCase):
    def test_preflight_covers_both_frozen_models(self) -> None:
        manifest = (
            ROOT / "infra" / "nautilus" / "resource-preflight-job.yaml"
        ).read_text(encoding="utf-8")

        self.assertEqual(manifest.count("scripts/run_multiuav_resource.py"), 2)
        self.assertEqual(manifest.count("--preflight-only"), 2)
        self.assertIn("--condition-order 1", manifest)
        self.assertIn("--condition-order 3", manifest)
        self.assertIn("qwen25_3b_cache_audit_nautilus_v1.json", manifest)
        self.assertIn("qwen25_3b_load_smoke_nautilus_v1.json", manifest)
        self.assertIn("qwen25_7b_cache_audit_nautilus_v1.json", manifest)
        self.assertIn("qwen25_7b_load_smoke_nautilus_v1.json", manifest)


if __name__ == "__main__":
    unittest.main()
