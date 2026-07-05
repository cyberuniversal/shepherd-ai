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

    def test_return_every_drone_maps_to_all_count(self) -> None:
        intent = parse_intent("Return every drone.")

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
        self.assertEqual(payload["parser"], "deterministic_v2")

    def test_empty_command_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_intent("   ")

    def test_search_open_field_for_missing_vehicle(self) -> None:
        intent = parse_intent("Search the open field for a missing vehicle.")

        self.assertEqual(intent.action, "search")
        self.assertIsNone(intent.count)
        self.assertEqual(intent.location, "open field")
        self.assertEqual(intent.target, "missing vehicle")
        self.assertEqual(intent.constraints, [])

    def test_highest_battery_water_tank_command(self) -> None:
        intent = parse_intent("Send the drone with the highest battery to inspect the water tank.")

        self.assertEqual(intent.action, "inspect")
        self.assertEqual(intent.count, 1)
        self.assertIsNone(intent.location)
        self.assertEqual(intent.target, "water tank")
        self.assertEqual(intent.constraints, ["highest battery"])

    def test_compound_canal_command_counts_multiple_drones(self) -> None:
        intent = parse_intent("Send two drones to the canal while one drone monitors the crops.")

        self.assertEqual(intent.action, "send")
        self.assertEqual(intent.count, 3)
        self.assertIsNone(intent.location)
        self.assertEqual(intent.target, "irrigation canal")
        self.assertEqual(intent.constraints, ["one drone monitors the crops"])

    def test_whichever_drone_counts_as_one(self) -> None:
        intent = parse_intent("Send whichever drone has the most battery to the greenhouse.")

        self.assertEqual(intent.action, "send")
        self.assertEqual(intent.count, 1)
        self.assertIsNone(intent.location)
        self.assertEqual(intent.target, "greenhouse")
        self.assertEqual(intent.constraints, ["highest battery"])

    def test_split_industrial_zone_constraint_is_preserved(self) -> None:
        intent = parse_intent(
            "Send four drones to split the industrial zone into equal sections and report anything unusual."
        )

        self.assertEqual(intent.action, "send")
        self.assertEqual(intent.count, 4)
        self.assertIsNone(intent.location)
        self.assertEqual(intent.target, "industrial zone")
        self.assertEqual(
            intent.constraints,
            ["split the industrial zone into equal sections", "report anything unusual"],
        )

    def test_multi_direction_assignment_is_constraint_not_single_location(self) -> None:
        intent = parse_intent("Send one drone north and another east.")

        self.assertEqual(intent.action, "send")
        self.assertEqual(intent.count, 2)
        self.assertIsNone(intent.location)
        self.assertIsNone(intent.target)
        self.assertEqual(intent.constraints, ["one drone north and another east"])

    def test_nearest_drone_and_back_to_base_constraints(self) -> None:
        nearest = parse_intent("Have the nearest drone check the irrigation canal.")
        returning = parse_intent("Send all available drones back to base.")

        self.assertEqual(nearest.constraints, ["nearest drone"])
        self.assertEqual(nearest.target, "irrigation canal")
        self.assertEqual(returning.action, "return")
        self.assertEqual(returning.count, "all")
        self.assertEqual(returning.target, "drones")
        self.assertEqual(returning.constraints, ["back to base"])

    def test_divide_field_constraint_is_preserved(self) -> None:
        intent = parse_intent("Divide the field between three drones and scan each section.")

        self.assertEqual(intent.action, "scan")
        self.assertEqual(intent.count, 3)
        self.assertIsNone(intent.location)
        self.assertEqual(intent.target, "field")
        self.assertEqual(intent.constraints, ["divide the field between three drones"])

    def test_open_vocabulary_inspection_target_is_extracted(self) -> None:
        intent = parse_intent("Send the nearest drone to inspect the livestock pen.")

        self.assertEqual(intent.action, "inspect")
        self.assertEqual(intent.count, 1)
        self.assertEqual(intent.target, "livestock pen")
        self.assertEqual(intent.constraints, ["nearest drone"])
        self.assertNotIn("target_not_stated", intent.notes)

    def test_open_vocabulary_capture_target_is_extracted(self) -> None:
        intent = parse_intent("Capture images of the red pickup truck.")

        self.assertEqual(intent.action, "capture")
        self.assertEqual(intent.target, "red pickup truck")
        self.assertNotIn("target_not_stated", intent.notes)

    def test_open_vocabulary_target_stops_before_constraint(self) -> None:
        intent = parse_intent("Scan the loading dock without crossing the road.")

        self.assertEqual(intent.action, "scan")
        self.assertEqual(intent.target, "loading dock")
        self.assertEqual(intent.constraints, ["without crossing the road"])

    def test_altitude_limit_constraint_is_preserved(self) -> None:
        spoken = parse_intent("Send two drones west but keep them below fifty meters.")
        digit = parse_intent("Send two drones west, but keep them below 50 meters.")
        target_altitude = parse_intent("Send two drones to inspect the tower below forty meters.")

        self.assertEqual(spoken.constraints, ["keep them below fifty meters"])
        self.assertEqual(digit.constraints, ["keep them below 50 meters"])
        self.assertEqual(target_altitude.target, "tower")
        self.assertEqual(target_altitude.constraints, ["below forty meters"])

    def test_audio_linked_command_variants_are_preserved(self) -> None:
        return_to_me = parse_intent("Check the field and return to me.")
        closest = parse_intent("Get the closest drone to inspect the storage area.")
        avoiding = parse_intent("Inspect the north field while avoiding the storage area.")
        compound = parse_intent("Dispatch one drone to the greenhouse then send two more to scan the west field.")
        bring_back = parse_intent("Bring all the drones back.")

        self.assertEqual(return_to_me.constraints, ["return to me"])
        self.assertEqual(closest.count, 1)
        self.assertEqual(closest.constraints, ["closest drone"])
        self.assertEqual(avoiding.target, "field")
        self.assertEqual(avoiding.constraints, ["while avoiding the storage area"])
        self.assertEqual(compound.target, "field")
        self.assertEqual(compound.constraints, ["one drone to the greenhouse"])
        self.assertEqual(bring_back.action, "return")
        self.assertEqual(bring_back.target, "drones")

    def test_audio_generalization_validation_location_target_patterns(self) -> None:
        stalled = parse_intent("Have two drones scan the service road for stalled vehicles.")
        roof = parse_intent("Check the lower roof for standing water after the rain.")
        returning = parse_intent("Send all available drones back to the launch area.")

        self.assertEqual(stalled.action, "scan")
        self.assertEqual(stalled.location, "service road")
        self.assertEqual(stalled.target, "stalled vehicles")
        self.assertEqual(roof.action, "inspect")
        self.assertEqual(roof.location, "lower roof")
        self.assertEqual(roof.target, "standing water")
        self.assertEqual(roof.constraints, ["after the rain"])
        self.assertEqual(returning.action, "return")
        self.assertEqual(returning.location, "launch area")
        self.assertEqual(returning.target, "drones")

    def test_audio_generalization_extended_action_and_constraint_patterns(self) -> None:
        mapped = parse_intent("Use three drones to map the outer fence from east to west.")
        photographed = parse_intent("Have the nearest drone photograph the damaged sign.")
        monitored = parse_intent("Monitor the main road until the ambulance arrives.")

        self.assertEqual(mapped.action, "scan")
        self.assertEqual(mapped.target, "outer fence")
        self.assertEqual(mapped.constraints, ["from east to west"])
        self.assertEqual(photographed.action, "capture")
        self.assertEqual(photographed.target, "damaged sign")
        self.assertEqual(photographed.constraints, ["nearest drone"])
        self.assertEqual(monitored.action, "scan")
        self.assertEqual(monitored.location, "main road")
        self.assertEqual(monitored.target, "main road")
        self.assertEqual(monitored.constraints, ["until the ambulance arrives"])

    def test_audio_generalization_compound_patterns_are_lossy_but_explicit(self) -> None:
        sent_then_return = parse_intent("Send one drone to the southern wall, then return it to the launch area.")
        divided = parse_intent("Send three drones to divide the campus into separate search areas.")

        self.assertEqual(sent_then_return.action, "send")
        self.assertEqual(sent_then_return.location, "southern wall")
        self.assertIsNone(sent_then_return.target)
        self.assertEqual(sent_then_return.constraints, ["then return it to the launch area"])
        self.assertEqual(divided.action, "search")
        self.assertEqual(divided.count, 3)
        self.assertEqual(divided.target, "campus")
        self.assertEqual(divided.constraints, ["divide the campus into separate search areas"])


if __name__ == "__main__":
    unittest.main()
