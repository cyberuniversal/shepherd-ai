import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week7_completion import (  # noqa: E402
    build_week7_completion_audit,
    render_week7_completion_markdown,
)


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Week7CompletionTests(unittest.TestCase):
    def _audit(self, evaluation: dict | None = None, deferrals: dict | None = None):
        return build_week7_completion_audit(
            evaluation=evaluation or _json("outputs/evaluations/week7_safety_development_v1.json"),
            policy=_json("datasets/safety/week7_safety_policy_v1.json"),
            acceptance_criteria=_json("docs/week7_acceptance_criteria.json"),
            research_deferrals=deferrals or _json("docs/week7_research_deferrals.json"),
            notebook_text=(ROOT / "notebooks/Notebook7_Safety.ipynb").read_text(encoding="utf-8"),
        )

    def test_complete_evidence_allows_week8_advancement(self) -> None:
        audit = self._audit()

        self.assertTrue(audit.advancement_allowed)
        self.assertEqual(audit.blockers, ())
        self.assertEqual(
            audit.decision,
            "week7_complete_for_advancement_to_week8_end_to_end_evaluation",
        )

    def test_mismatched_case_result_blocks_advancement(self) -> None:
        evaluation = copy.deepcopy(_json("outputs/evaluations/week7_safety_development_v1.json"))
        evaluation["summary"]["expected_status_matches"] -= 1

        audit = self._audit(evaluation=evaluation)

        self.assertFalse(audit.advancement_allowed)
        self.assertIn("all_expected_statuses_match", audit.blockers)

    def test_missing_research_deferrals_block_advancement(self) -> None:
        audit = self._audit(deferrals={"scope": "week7_research_deferrals_v1", "deferrals": {}})

        self.assertFalse(audit.advancement_allowed)
        self.assertIn("physical_safety_not_claimed", audit.blockers)

    def test_markdown_preserves_scope_and_decision(self) -> None:
        markdown = render_week7_completion_markdown(self._audit())

        self.assertIn("Week 7 Completion Gate Audit", markdown)
        self.assertIn("not physical-flight safety evidence", markdown)
        self.assertIn("Advancement allowed", markdown)


if __name__ == "__main__":
    unittest.main()
