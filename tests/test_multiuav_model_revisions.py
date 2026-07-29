import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from shepherd_ai.multiuav_model_revisions import (
    ModelRevision,
    REGISTERED_MODEL_REVISIONS,
    build_model_revision_audit,
    validate_model_revisions,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_multiuav_model_revisions.py"


class MultiUavModelRevisionTests(unittest.TestCase):
    def test_registered_revisions_are_exact_immutable_commits(self) -> None:
        result = validate_model_revisions()

        self.assertTrue(result["valid"])
        self.assertEqual(result["model_count"], 2)
        self.assertEqual(
            [item.revision for item in REGISTERED_MODEL_REVISIONS],
            [
                "aa8e72537993ba99e69dfaafa59ed015b17504d1",
                "a09a35458c702b33eeacc393d103063234e8bc28",
            ],
        )

    def test_mutable_revision_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "40-character commit"):
            validate_model_revisions(
                (
                    ModelRevision(
                        model_id="Qwen/Qwen2.5-3B-Instruct",
                        revision="main",
                        role="primary_scale",
                    ),
                    REGISTERED_MODEL_REVISIONS[1],
                )
            )

    def test_remote_audit_requires_exact_id_and_revision(self) -> None:
        def fetch(url: str) -> dict:
            match = next(
                item
                for item in REGISTERED_MODEL_REVISIONS
                if item.revision_api_url == url
            )
            return {
                "id": match.model_id,
                "sha": match.revision,
                "lastModified": "2025-01-01T00:00:00.000Z",
            }

        result = build_model_revision_audit(
            fetch_json=fetch,
            resolved_at_utc="2026-07-29T00:00:00+00:00",
        )

        self.assertTrue(result["valid"])
        self.assertTrue(result["remote_verification_performed"])
        self.assertTrue(all(item["remote_verified"] for item in result["models"]))
        self.assertFalse(result["weights_downloaded"])
        self.assertFalse(result["model_invoked"])

    def test_offline_cli_does_not_claim_remote_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "audit.json"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--output",
                    str(output),
                    "--skip-remote-verification",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(output.read_text(encoding="utf-8"))

        self.assertTrue(result["valid"])
        self.assertFalse(result["remote_verification_performed"])
        self.assertEqual(
            result["claim_status"],
            "immutable_model_registry_validated_offline_only",
        )


if __name__ == "__main__":
    unittest.main()
