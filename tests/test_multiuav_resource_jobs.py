from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class MultiUavResourceJobTests(unittest.TestCase):
    def test_preflight_and_campaign_use_the_same_pinned_checkout(self) -> None:
        pins = []
        for name in ("resource-preflight-job.yaml", "resource-job.yaml"):
            manifest = (ROOT / "infra" / "nautilus" / name).read_text(
                encoding="utf-8"
            )
            match = re.search(
                r"name: SHEPHERD_GIT_COMMIT\s+value: ([0-9a-f]{40})", manifest
            )
            self.assertIsNotNone(match)
            pins.append(match.group(1))

        self.assertEqual(pins[0], pins[1])

    def test_frozen_resource_bindings_preserve_registered_crlf_bytes(self) -> None:
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")

        for path in (
            "datasets/multiuav_plat/accuracy_case_manifest_v1.json",
            "datasets/multiuav_plat/accuracy_protocol_freeze_v1.json",
            "datasets/multiuav_plat/intervention_dataset_v1.json",
            "datasets/multiuav_plat/resource_hardware_protocol_v1.json",
            "datasets/multiuav_plat/resource_run_configs_v1.json",
            "datasets/multiuav_plat/resource_schedule_v1.json",
        ):
            self.assertIn(f"{path} text eol=crlf", attributes)

    def test_preflight_queue_deadline_allows_for_scarce_gpu_capacity(self) -> None:
        manifest = (
            ROOT / "infra" / "nautilus" / "resource-preflight-job.yaml"
        ).read_text(encoding="utf-8")

        self.assertIn("activeDeadlineSeconds: 604800", manifest)

    def test_attempt_two_uses_new_durable_paths_without_container_retry(self) -> None:
        preflight = (
            ROOT / "infra" / "nautilus" / "resource-preflight-job.yaml"
        ).read_text(encoding="utf-8")
        campaign = (
            ROOT / "infra" / "nautilus" / "resource-job.yaml"
        ).read_text(encoding="utf-8")

        self.assertIn("name: shepherd-ai-resource-preflight-v2", preflight)
        self.assertIn("/workspace/results/resource-v2-preflight", preflight)
        self.assertGreaterEqual(preflight.count('memory: 32Gi'), 2)
        self.assertGreaterEqual(preflight.count('cpu: "2"'), 2)
        self.assertIn("name: shepherd-ai-resource-v1-a2", campaign)
        self.assertIn("/workspace/results/resource-v1-attempt2", campaign)
        self.assertIn("restartPolicy: Never", campaign)

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
