import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import ground_intent, load_map_locations  # noqa: E402
from shepherd_ai.grounding_clarification import apply_clarification_choices, build_clarification_report  # noqa: E402
from shepherd_ai.intent import parse_intent  # noqa: E402


MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
CLARIFICATION_SCRIPT = ROOT / "scripts" / "create_grounding_clarification_report.py"
APPLY_SCRIPT = ROOT / "scripts" / "apply_grounding_clarification.py"


class GroundingClarificationTests(unittest.TestCase):
    def test_ambiguous_grounding_produces_candidate_question(self) -> None:
        grounded = ground_intent(
            parse_intent("Monitor the road until the ambulance arrives."),
            load_map_locations(MAP_PATH),
        )

        report = build_clarification_report(grounded)

        self.assertTrue(report.blocks_planning)
        self.assertEqual(len(report.requests), 2)
        first_request = report.requests[0]
        self.assertEqual(first_request.reason, "ambiguous_map_reference")
        self.assertIn("Which map location", first_request.question)
        self.assertEqual(
            {option.location_id for option in first_request.options},
            {"loc_service_road", "loc_main_road"},
        )

    def test_unresolved_grounding_requests_map_alias_or_dataset_update(self) -> None:
        grounded = ground_intent(
            parse_intent("Capture images of the red pickup truck."),
            load_map_locations(MAP_PATH),
        )

        report = build_clarification_report(grounded)

        self.assertTrue(report.blocks_planning)
        self.assertEqual(len(report.requests), 1)
        self.assertEqual(report.requests[0].reason, "unresolved_map_reference")
        self.assertIn("add the location", report.requests[0].question)

    def test_grounded_command_has_no_clarification_requests(self) -> None:
        grounded = ground_intent(
            parse_intent("Send two drones north and inspect the crops."),
            load_map_locations(MAP_PATH),
        )

        report = build_clarification_report(grounded)

        self.assertFalse(report.blocks_planning)
        self.assertEqual(report.requests, ())

    def test_apply_clarification_choices_resolves_ambiguous_references(self) -> None:
        locations = load_map_locations(MAP_PATH)
        grounded = ground_intent(
            parse_intent("Monitor the road until the ambulance arrives."),
            locations,
        )

        resolved = apply_clarification_choices(
            grounded,
            {"location": "loc_service_road", "target": "loc_service_road"},
            locations=locations,
        )
        report = build_clarification_report(resolved)
        refs = {reference.field: reference for reference in resolved.references}

        self.assertTrue(resolved.ready_for_planning)
        self.assertEqual(resolved.issues, ())
        self.assertEqual(refs["location"].location.id, "loc_service_road")
        self.assertEqual(refs["location"].note, "operator_selected_ambiguous_candidate")
        self.assertFalse(report.blocks_planning)
        self.assertEqual(report.requests, ())

    def test_apply_clarification_choices_rejects_invalid_candidate(self) -> None:
        locations = load_map_locations(MAP_PATH)
        grounded = ground_intent(
            parse_intent("Monitor the road until the ambulance arrives."),
            locations,
        )

        with self.assertRaisesRegex(ValueError, "must be one of the ambiguous candidates"):
            apply_clarification_choices(
                grounded,
                {"location": "loc_greenhouse"},
                locations=locations,
            )

    def test_clarification_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "clarification.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(CLARIFICATION_SCRIPT),
                    "--command",
                    "Monitor the road until the ambulance arrives.",
                    "--map",
                    str(MAP_PATH),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn("blocks_planning", completed.stdout)
        self.assertTrue(payload["clarification_report"]["blocks_planning"])
        self.assertEqual(len(payload["clarification_report"]["requests"]), 2)

    def test_apply_clarification_cli_writes_resolved_grounding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clarification_output = Path(tmp) / "clarification.json"
            resolved_output = Path(tmp) / "resolved.json"
            subprocess.run(
                [
                    sys.executable,
                    str(CLARIFICATION_SCRIPT),
                    "--command",
                    "Monitor the road until the ambulance arrives.",
                    "--map",
                    str(MAP_PATH),
                    "--output",
                    str(clarification_output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(APPLY_SCRIPT),
                    "--grounded-json",
                    str(clarification_output),
                    "--map",
                    str(MAP_PATH),
                    "--choice",
                    "location=loc_service_road",
                    "--choice",
                    "target=loc_service_road",
                    "--output",
                    str(resolved_output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(resolved_output.read_text(encoding="utf-8"))

        self.assertIn("remaining_requests", completed.stdout)
        self.assertFalse(payload["clarification_report"]["blocks_planning"])
        self.assertEqual(payload["clarification_report"]["requests"], [])
        self.assertEqual(payload["operator_choices"]["location"], "loc_service_road")
        self.assertEqual(payload["resolved_grounded_intent"]["intent"]["text"], "Monitor the road until the ambulance arrives.")


if __name__ == "__main__":
    unittest.main()
