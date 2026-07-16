from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.clarification_dialogue import ClarificationSession  # noqa: E402
from shepherd_ai.grounding import ground_intent, load_map_locations  # noqa: E402
from shepherd_ai.intent import parse_intent  # noqa: E402


MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"


def _session(text: str = "Check if there is any traffic on the road.") -> ClarificationSession:
    locations = load_map_locations(MAP_PATH)
    return ClarificationSession(ground_intent(parse_intent(text), locations), locations)


class ClarificationDialogueTests(unittest.TestCase):
    def test_valid_choice_requires_confirmation_and_preserves_original_text(self) -> None:
        session = _session()

        response = session.submit_choices({"target": "loc_service_road"})
        self.assertTrue(response["accepted"])
        self.assertEqual(session.snapshot()["status"], "awaiting_confirmation")
        session.confirm()

        snapshot = session.snapshot()
        self.assertEqual(snapshot["status"], "confirmed")
        self.assertEqual(snapshot["original_command"], "Check if there is any traffic on the road.")
        selected = next(
            reference
            for reference in snapshot["resolved_grounded_intent"]["references"]
            if reference["field"] == "target"
        )
        self.assertEqual(selected["location"]["id"], "loc_service_road")
        self.assertEqual(
            [event["event_type"] for event in snapshot["events"]],
            ["clarification_requested", "response_accepted", "operator_confirmed"],
        )

    def test_invalid_choice_is_recorded_and_session_stays_open(self) -> None:
        session = _session()

        response = session.submit_choices({"target": "loc_not_a_candidate"})

        self.assertFalse(response["accepted"])
        self.assertEqual(session.snapshot()["status"], "awaiting_response")
        self.assertEqual(session.snapshot()["events"][-1]["event_type"], "response_rejected")

    def test_operator_can_cancel_without_resolving(self) -> None:
        session = _session()

        session.cancel("operator_declined")

        snapshot = session.snapshot()
        self.assertEqual(snapshot["status"], "cancelled")
        self.assertEqual(snapshot["events"][-1]["details"]["reason"], "operator_declined")

    def test_timeout_is_terminal_and_recorded(self) -> None:
        session = _session()

        session.timeout()

        snapshot = session.snapshot()
        self.assertEqual(snapshot["status"], "timed_out")
        self.assertEqual(snapshot["events"][-1]["event_type"], "clarification_timed_out")


if __name__ == "__main__":
    unittest.main()
