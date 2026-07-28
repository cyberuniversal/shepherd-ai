import json
from pathlib import Path
import unittest

from shepherd_ai.week9_completion import (
    build_week9_completion_audit,
    render_week9_completion_markdown,
)


ROOT = Path(__file__).resolve().parents[1]


class Week9CompletionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.paper = (ROOT / "reports/shepherd_ai_paper_draft.md").read_text(encoding="utf-8")
        self.bibliography = (ROOT / "reports/week9_bibliography.md").read_text(
            encoding="utf-8"
        )
        self.notebook = (
            ROOT / "notebooks/Notebook9_Legacy_Paper_Artifacts.ipynb"
        ).read_text(encoding="utf-8")
        self.evidence = json.loads(
            (ROOT / "outputs/evaluations/week9_paper_evidence.json").read_text(encoding="utf-8")
        )
        self.artifacts = {"figure": True, "table": True, "report": True}

    def test_current_week9_draft_passes_all_gates(self) -> None:
        audit = build_week9_completion_audit(
            paper_text=self.paper,
            bibliography_text=self.bibliography,
            notebook_text=self.notebook,
            evidence=self.evidence,
            artifact_status=self.artifacts,
        )

        self.assertTrue(audit.completion_allowed)
        self.assertEqual(audit.blockers, ())

    def test_missing_methodology_blocks_completion(self) -> None:
        audit = build_week9_completion_audit(
            paper_text=self.paper.replace("## 8. Methodology", "## Method Removed"),
            bibliography_text=self.bibliography,
            notebook_text=self.notebook,
            evidence=self.evidence,
            artifact_status=self.artifacts,
        )

        self.assertFalse(audit.completion_allowed)
        self.assertIn("all_roadmap_draft_sections_present", audit.blockers)

    def test_unsupported_claim_limit_blocks_completion(self) -> None:
        evidence = json.loads(json.dumps(self.evidence))
        evidence["claim_limits"]["novelty_claimed"] = True
        audit = build_week9_completion_audit(
            paper_text=self.paper,
            bibliography_text=self.bibliography,
            notebook_text=self.notebook,
            evidence=evidence,
            artifact_status=self.artifacts,
        )

        self.assertIn("claim_limits_preserved", audit.blockers)

    def test_markdown_distinguishes_draft_from_publication_readiness(self) -> None:
        audit = build_week9_completion_audit(
            paper_text=self.paper,
            bibliography_text=self.bibliography,
            notebook_text=self.notebook,
            evidence=self.evidence,
            artifact_status=self.artifacts,
        )
        report = render_week9_completion_markdown(audit)

        self.assertIn("not publication readiness", report)
        self.assertIn("Completion allowed: `true`", report)


if __name__ == "__main__":
    unittest.main()
