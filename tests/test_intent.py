import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.intent import parse_intent  # noqa: E402


class IntentParserTests(unittest.TestCase):
    def test_roadmap_compound_command(self) -> None:
        intent = parse_intent("Send two drones north and inspect the crops.")

        self.assertEqual(intent.action, "inspect")
        self.assertEqual(intent.count, 2)
        self.assertEqual(intent.location, "north")
        self.assertEqual(intent.target, "crops")
        self.assertEqual(intent.constraints, [])

    def test_return_all_drones(self) -> None:
        intent = parse_intent("Return all drones.")

        self.assertEqual(intent.action, "return")
        self.assertEqual(intent.count, "all")
        self.assertIsNone(intent.location)
        self.assertEqual(intent.target, "drones")

    def test_missing_fields_are_not_guessed(self) -> None:
        intent = parse_intent("Inspect the greenhouse.")

        self.assertEqual(intent.action, "inspect")
        self.assertIsNone(intent.count)
        self.assertIsNone(intent.location)
        self.assertEqual(intent.target, "greenhouse")
        self.assertIn("count_not_stated", intent.notes)
        self.assertIn("location_not_stated", intent.notes)

    def test_json_serialization(self) -> None:
        payload = json.loads(parse_intent("Scan the western field.").to_json())

        self.assertEqual(payload["action"], "scan")
        self.assertEqual(payload["location"], "west")
        self.assertEqual(payload["target"], "field")
        self.assertEqual(payload["parser"], "deterministic_v0")

    def test_empty_command_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_intent("   ")


if __name__ == "__main__":
    unittest.main()
