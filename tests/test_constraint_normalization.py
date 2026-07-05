import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.constraint_normalization import (  # noqa: E402
    constraint_semantic_signatures,
    normalize_constraint,
    normalize_constraints,
)


class ConstraintNormalizationTests(unittest.TestCase):
    def test_altitude_constraint_number_word_and_digit_have_same_signature(self) -> None:
        word = normalize_constraint("keep them below fifty meters")
        digit = normalize_constraint("keep them below 50 metres")

        self.assertEqual(word.kind, "altitude_limit")
        self.assertEqual(word.relation, "below")
        self.assertEqual(word.value, 50)
        self.assertEqual(word.unit, "meters")
        self.assertEqual(word.semantic_signature(), digit.semantic_signature())

    def test_under_and_no_higher_than_altitude_forms_are_supported(self) -> None:
        under = normalize_constraint("under forty meters")
        no_higher = normalize_constraint("no higher than twenty-five meters")

        self.assertEqual(under.semantic_signature(), ("altitude_limit", "below", 40, "meters"))
        self.assertEqual(no_higher.semantic_signature(), ("altitude_limit", "below", 25, "meters"))

    def test_unknown_constraint_is_preserved_as_unparsed(self) -> None:
        constraint = normalize_constraint("return to base")

        self.assertEqual(constraint.kind, "unparsed_constraint")
        self.assertEqual(constraint.source_text, "return to base")
        self.assertEqual(constraint.notes, ["no_supported_canonical_form"])
        self.assertNotEqual(
            normalize_constraint("return to base").semantic_signature(),
            normalize_constraint("return to me").semantic_signature(),
        )

    def test_empty_constraint_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_constraint(" ")

    def test_list_normalization_and_signature_set(self) -> None:
        constraints = normalize_constraints(["below thirty meters", "return to me"])

        self.assertEqual(len(constraints), 2)
        self.assertIn(("altitude_limit", "below", 30, "meters"), constraint_semantic_signatures(["below thirty meters"]))


if __name__ == "__main__":
    unittest.main()
