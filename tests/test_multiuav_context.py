from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_context import (  # noqa: E402
    privileged_noninterference_check,
    project_agent_visible_context,
    validate_agent_visible_context,
)


def _session() -> dict:
    return {
        "id": "session-1",
        "name": "hidden descriptive name",
        "task_type": "target_assignment",
        "canvas_width": 1000,
        "canvas_height": 800,
        "is_distance_3d": True,
        "status": "active",
        "history": [{"secret": "trajectory"}],
        "statistics": {"secret": "completion"},
        "targets": [{"id": "target-secret"}],
        "obstacles": [{"id": "obstacle-secret"}],
        "drones": [
            {
                "id": "drone-1",
                "name": "Drone 1",
                "model": "Model-A",
                "status": "idle",
                "position": {"x": 1, "y": 2, "z": 0},
                "battery_level": 100,
                "private_extension": "not projected",
            }
        ],
        "environment": {
            "id": "env-1",
            "name": "Clear",
            "weather": "clear",
            "secret_forecast": "not projected",
        },
        "tasks": [
            {
                "id": "task-1",
                "content": "Take off.",
                "content_aliases": ["Launch."],
                "related_apis": [{"endpoint": "secret"}],
                "commands": [{"secret": True}],
                "execution_check_apis": {"secret": True},
                "is_done": False,
                "is_passed": False,
            }
        ],
    }


class MultiUavContextTests(unittest.TestCase):
    def test_projection_uses_positive_allowlist(self) -> None:
        context = project_agent_visible_context(
            _session(),
            task_id="task-1",
            instruction="Take off.",
        )

        self.assertEqual(context["role"], "AGENT")
        self.assertEqual(context["instruction"], "Take off.")
        self.assertNotIn("name", context["session"])
        self.assertNotIn("targets", context)
        self.assertNotIn("obstacles", context)
        self.assertNotIn("private_extension", context["drones"][0])
        self.assertNotIn("secret_forecast", context["environment"])
        self.assertFalse(
            context["observation_contract"]["global_targets_visible"]
        )

    def test_privileged_values_cannot_change_projection(self) -> None:
        self.assertTrue(
            privileged_noninterference_check(
                _session(),
                task_id="task-1",
                instruction="Take off.",
            )
        )

    def test_recursive_validator_rejects_privileged_field(self) -> None:
        context = project_agent_visible_context(
            _session(),
            task_id="task-1",
            instruction="Take off.",
        )
        context["drones"][0]["execution_check_apis"] = {}

        with self.assertRaisesRegex(ValueError, "privileged fields"):
            validate_agent_visible_context(context)

    def test_validator_rejects_nonprivileged_field_outside_allowlist(self) -> None:
        context = project_agent_visible_context(
            _session(),
            task_id="task-1",
            instruction="Take off.",
        )
        context["environment"]["task_description"] = "leaking metadata"

        with self.assertRaisesRegex(ValueError, "outside the allowlist"):
            validate_agent_visible_context(context)

    def test_validator_rejects_global_target_visibility(self) -> None:
        context = project_agent_visible_context(
            _session(),
            task_id="task-1",
            instruction="Take off.",
        )
        context["observation_contract"]["global_targets_visible"] = True

        with self.assertRaisesRegex(ValueError, "global targets"):
            validate_agent_visible_context(context)


if __name__ == "__main__":
    unittest.main()
