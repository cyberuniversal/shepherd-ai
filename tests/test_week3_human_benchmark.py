from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations  # noqa: E402
from shepherd_ai.week3_human_benchmark import (  # noqa: E402
    build_human_grounding_packet,
    render_human_grounding_packet_markdown,
)


MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"


class Week3HumanBenchmarkTests(unittest.TestCase):
    def test_build_human_grounding_packet_creates_blank_slots_for_map_records(self) -> None:
        locations = load_map_locations(MAP_PATH)

        packet = build_human_grounding_packet(locations)

        self.assertEqual(len(packet), len(locations) + 2)
        self.assertEqual(packet[0].label_status, "needs_human_written_command")
        self.assertEqual(packet[0].text, "")
        self.assertEqual(packet[0].expected_grounding["target"]["status"], "grounded")
        self.assertEqual(packet[-2].expected_grounding["location"]["status"], "ambiguous")
        self.assertEqual(packet[-1].expected_grounding["target"]["status"], "unresolved")

    def test_render_human_grounding_packet_markdown_warns_blank_slots_are_not_data(self) -> None:
        packet = build_human_grounding_packet(load_map_locations(MAP_PATH))

        markdown = render_human_grounding_packet_markdown(packet)

        self.assertIn("Blank slots are not benchmark data", markdown)
        self.assertIn("Synthetic examples and model-generated text", markdown)
        self.assertIn('"status": "grounded"', markdown)


if __name__ == "__main__":
    unittest.main()
