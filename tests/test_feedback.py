from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.feedback import FeedbackLog, simulate_mission_status_updates  # noqa: E402
from shepherd_ai.scheduling import Assignment, ScheduleResult  # noqa: E402


class FeedbackTests(unittest.TestCase):
    def test_feedback_log_preserves_ordered_status_updates(self) -> None:
        log = FeedbackLog()

        log.add("input", "command_received", "Command accepted.")
        log.add("grounding", "clarification_required", "Choose a road.", blocks_progress=True)

        payload = log.to_dict()
        self.assertEqual([event["sequence"] for event in payload["events"]], [1, 2])
        self.assertEqual(payload["latest_status"], "clarification_required")
        self.assertTrue(payload["blocked"])

    def test_schedule_status_updates_are_ordered_and_labeled_simulated(self) -> None:
        schedule = ScheduleResult(
            strategy="least_loaded",
            assignments=(
                Assignment(
                    task_id="task_1",
                    drone_id="drone_alpha",
                    strategy="least_loaded",
                    start_min=0.0,
                    end_min=3.0,
                    duration_min=3.0,
                    travel_distance_m=100.0,
                    target_location_id="loc_north_field",
                    target_name="North Field",
                    action="scan",
                ),
            ),
            unassigned_tasks=(),
            metrics={},
        )

        updates = simulate_mission_status_updates(schedule)

        self.assertEqual([update["status"] for update in updates], ["task_started", "task_completed"])
        self.assertTrue(all(update["mode"] == "schedule_based_simulation" for update in updates))
        self.assertEqual([update["sequence"] for update in updates], [1, 2])


if __name__ == "__main__":
    unittest.main()
