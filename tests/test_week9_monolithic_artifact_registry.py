import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = (
    ROOT
    / "outputs"
    / "evaluations"
    / "week9_monolithic_qwen25_7b_artifact_registry_v1.json"
)


class Week9MonolithicArtifactRegistryTests(unittest.TestCase):
    def test_registry_preserves_evidence_and_claim_limits(self) -> None:
        record = json.loads(REGISTRY.read_text(encoding="utf-8"))

        self.assertEqual(record["evaluation"]["case_count"], 38)
        self.assertEqual(
            record["inference"]["model_revision"],
            "a09a35458c702b33eeacc393d103063234e8bc28",
        )
        self.assertEqual(len(record["artifact"]["sha256"]), 64)
        self.assertEqual(record["artifact"]["archive_size_bytes"], 22368)
        self.assertEqual(record["artifact"]["zip_integrity_check"], "passed")
        self.assertFalse(record["research_limits"]["fresh_human_heldout"])
        self.assertTrue(record["research_limits"]["reuses_development_evidence"])
        self.assertFalse(record["research_limits"]["raw_output_committed_to_git"])
        self.assertEqual(
            record["research_limits"]["paper_claim_status"],
            "diagnostic_only",
        )


if __name__ == "__main__":
    unittest.main()
