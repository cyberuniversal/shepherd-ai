import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.mission_decomposition import decompose_mission_command


class MissionDecompositionTests(unittest.TestCase):
    def test_decomposes_exact_week8_roadmap_command(self) -> None:
        result = decompose_mission_command(
            "Send two drones north to inspect crops and one drone east to inspect irrigation."
        )

        self.assertEqual(result.status, "decomposed")
        self.assertEqual(result.total_requested_drones, 3)
        self.assertEqual(
            [clause.text for clause in result.clauses],
            [
                "Send two drones north to inspect crops",
                "one drone east to inspect irrigation",
            ],
        )
        self.assertEqual([clause.intent.count for clause in result.clauses], [2, 1])
        self.assertEqual([clause.intent.location for clause in result.clauses], ["north", "east"])
        self.assertEqual(
            [clause.intent.target for clause in result.clauses],
            ["crops", "irrigation canal"],
        )

    def test_does_not_split_a_shared_target_conjunction(self) -> None:
        result = decompose_mission_command("Send two drones north to inspect crops and irrigation.")

        self.assertEqual(result.status, "single_clause")
        self.assertEqual(len(result.clauses), 1)

    def test_marks_unseparated_multiple_drone_groups_for_clarification(self) -> None:
        result = decompose_mission_command(
            "Inspect north with two drones; inspect irrigation with one drone."
        )

        self.assertEqual(result.status, "clarification_required")
        self.assertEqual(result.clauses, ())
        self.assertIn("multiple_drone_groups_without_supported_boundary", result.issues)

    def test_rejects_empty_command(self) -> None:
        with self.assertRaisesRegex(ValueError, "command must not be empty"):
            decompose_mission_command("  ")


if __name__ == "__main__":
    unittest.main()
