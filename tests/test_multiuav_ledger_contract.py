import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_context import project_agent_visible_context  # noqa: E402
from shepherd_ai.multiuav_ledger_contract import (  # noqa: E402
    parse_evidence_ledger,
    validate_evidence_ledger,
)


def _context() -> dict:
    return project_agent_visible_context(
        {
            "id": "session-1",
            "task_type": "area_search",
            "canvas_width": 100,
            "canvas_height": 80,
            "status": "active",
            "drones": [
                {
                    "id": "drone-1",
                    "name": "Drone 1",
                    "status": "idle",
                    "position": {"x": 0, "y": 0, "z": 0},
                }
            ],
            "environment": {"id": "env-1", "weather": "clear"},
        },
        task_id="task-1",
        instruction="Have Drone 1 hover.",
    )


def _ledger(**changes) -> str:
    payload = {
        "evidence": [
            {"source_path": "drones[0].id", "claim": "Drone is visible."}
        ],
        "missing_operator_facts": [],
        "conflicts": [],
        "provisional_decision": "EXECUTE",
        "reason": "Visible drone can hover.",
    }
    payload.update(changes)
    return json.dumps(payload)


class MultiUavLedgerContractTests(unittest.TestCase):
    def test_valid_ledger_paths_are_verified(self) -> None:
        parsed = parse_evidence_ledger(_ledger())
        result = validate_evidence_ledger(parsed, _context())

        self.assertTrue(result.valid)
        self.assertEqual(result.verified_evidence_paths, ("drones[0].id",))

    def test_unknown_and_privileged_paths_are_contained(self) -> None:
        unknown = validate_evidence_ledger(
            parse_evidence_ledger(
                _ledger(
                    evidence=[
                        {
                            "source_path": "drones[9].id",
                            "claim": "Invented drone.",
                        }
                    ]
                )
            ),
            _context(),
        )
        privileged = validate_evidence_ledger(
            parse_evidence_ledger(
                _ledger(
                    evidence=[
                        {
                            "source_path": "execution_check_apis.secret",
                            "claim": "Hidden answer.",
                        }
                    ]
                )
            ),
            _context(),
        )

        self.assertEqual(
            unknown.containment_stage,
            "pre_plan_evidence_provenance",
        )
        self.assertEqual(
            privileged.issues[0].code,
            "privileged_evidence_path",
        )

    def test_inconsistent_provisional_decision_is_contained(self) -> None:
        result = validate_evidence_ledger(
            parse_evidence_ledger(
                _ledger(missing_operator_facts=["Required altitude is absent."])
            ),
            _context(),
        )

        self.assertFalse(result.valid)
        self.assertEqual(
            result.containment_stage,
            "pre_plan_decision_consistency",
        )

    def test_malformed_ledger_is_preserved(self) -> None:
        parsed = parse_evidence_ledger("not json")
        result = validate_evidence_ledger(parsed, _context())

        self.assertEqual(parsed.parse_status, "PARSE_ERROR")
        self.assertEqual(result.containment_stage, "pre_plan_ledger_parse")
        self.assertEqual(parsed.raw_output, "not json")

    def test_nontext_provisional_decision_is_parse_error(self) -> None:
        parsed = parse_evidence_ledger(
            _ledger(provisional_decision=["EXECUTE"])
        )

        self.assertEqual(parsed.parse_status, "PARSE_ERROR")
        self.assertEqual(parsed.error_code, "invalid_provisional_decision")


if __name__ == "__main__":
    unittest.main()
