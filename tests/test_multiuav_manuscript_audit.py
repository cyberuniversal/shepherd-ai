import json
from pathlib import Path
import tempfile
import unittest

from shepherd_ai.multiuav_manuscript_audit import audit_multiuav_manuscript


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "reports/multiuav_validation_placement_manuscript_v1.md"


class MultiUavManuscriptAuditTests(unittest.TestCase):
    def test_current_manuscript_passes_internal_traceability(self) -> None:
        audit = audit_multiuav_manuscript(ROOT)

        self.assertTrue(audit["valid"])
        self.assertEqual(
            audit["status"],
            "manuscript_internal_traceability_passed_external_review_pending",
        )
        self.assertFalse(audit["final_submission_ready"])
        self.assertFalse(audit["raw_model_outputs_accessed"])
        self.assertFalse(audit["hidden_labels_accessed"])
        self.assertGreaterEqual(len(audit["artifact_bindings"]), 12)
        self.assertEqual(audit["failed_checks"], [])

    def test_missing_claim_limit_fails_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manuscript = Path(temporary) / "manuscript.md"
            text = MANUSCRIPT.read_text(encoding="utf-8").replace(
                "GPU-board energy is not workstation, simulator, network, or UAV energy.",
                "GPU-board energy was measured.",
            )
            manuscript.write_text(text, encoding="utf-8")

            audit = audit_multiuav_manuscript(ROOT, manuscript_path=manuscript)

        self.assertFalse(audit["valid"])
        self.assertIn("gpu_board_energy_scope_disclosed", audit["failed_checks"])

    def test_resource_manifest_mutation_is_rejected(self) -> None:
        source = ROOT / "outputs/evaluations/multiuav_resource_reporting_v1/manifest.json"
        with tempfile.TemporaryDirectory() as temporary:
            manifest_path = Path(temporary) / "manifest.json"
            manifest = json.loads(source.read_text(encoding="utf-8"))
            manifest["status"] = "mutated"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            audit = audit_multiuav_manuscript(
                ROOT, resource_manifest_path=manifest_path
            )

        self.assertFalse(audit["valid"])
        self.assertIn("resource_reporting_manifest_valid", audit["failed_checks"])


if __name__ == "__main__":
    unittest.main()
