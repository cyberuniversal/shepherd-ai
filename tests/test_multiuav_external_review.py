import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from shepherd_ai.multiuav_external_review import build_external_review_packet


ROOT = Path(__file__).resolve().parents[1]


class MultiUavExternalReviewTests(unittest.TestCase):
    def test_builds_unreviewed_hash_bound_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            result = build_external_review_packet(
                repository_root=ROOT,
                packet_path=output / "packet.md",
            )

            packet = (output / "packet.md").read_text(encoding="utf-8")
            self.assertEqual(
                result["status"], "external_review_packet_ready_review_not_received"
            )
            self.assertFalse(result["external_review_received"])
            self.assertIsNone(result["reviewer_id"])
            self.assertIsNone(result["review_artifact"])
            self.assertGreaterEqual(len(result["artifact_bindings"]), 8)
            text_binding = result["artifact_bindings"]["accuracy_contrast_table"]
            figure_binding = result["artifact_bindings"]["accuracy_primary_figure"]
            contrast_path = (
                ROOT
                / "outputs"
                / "tables"
                / "multiuav_accuracy_registered_contrasts_v1.csv"
            )
            canonical_contrast = contrast_path.read_text(
                encoding="utf-8-sig"
            ).encode("utf-8")
            self.assertEqual(text_binding["hash_basis"], "utf8_lf_normalized")
            self.assertEqual(
                text_binding["sha256"],
                hashlib.sha256(canonical_contrast).hexdigest(),
            )
            self.assertEqual(figure_binding["hash_basis"], "raw_bytes")
            self.assertIn("Do not mark this packet as reviewed", packet)
            self.assertIn("Reviewer response fields", packet)
            self.assertEqual(
                hashlib.sha256((output / "packet.md").read_bytes()).hexdigest(),
                result["packet_sha256"],
            )

    def test_rejects_failed_internal_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            bad_audit = output / "audit.json"
            bad_audit.write_text('{"valid": false}', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "traceability"):
                build_external_review_packet(
                    repository_root=ROOT,
                    internal_audit_path=bad_audit,
                    packet_path=output / "packet.md",
                )

    def test_rejects_stale_internal_audit(self) -> None:
        source = (
            ROOT
            / "outputs"
            / "evaluations"
            / "multiuav_manuscript_traceability_v1.json"
        )
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            stale_audit = output / "audit.json"
            audit = json.loads(source.read_text(encoding="utf-8"))
            audit["artifact_bindings"]["manuscript"]["sha256"] = "0" * 64
            stale_audit.write_text(json.dumps(audit), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "stale"):
                build_external_review_packet(
                    repository_root=ROOT,
                    internal_audit_path=stale_audit,
                    packet_path=output / "packet.md",
                )


if __name__ == "__main__":
    unittest.main()
