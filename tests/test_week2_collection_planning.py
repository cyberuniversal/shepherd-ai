import unittest

from shepherd_ai.week2_collection_planning import (
    build_week2_collection_plan,
    render_week2_collection_plan_markdown,
)


class Week2CollectionPlanningTests(unittest.TestCase):
    def test_prioritizes_fields_from_error_counts(self) -> None:
        plan = build_week2_collection_plan(
            span_summary={
                "records": 2,
                "span_field_counts": {"action": 2, "target": 1, "constraint": 1},
            },
            evaluation_summary={
                "records": 2,
                "entity_f1": 0.5,
                "entity_precision": 0.5,
                "entity_recall": 0.5,
                "token_accuracy": 0.75,
            },
            error_analysis={
                "false_negative_entity_counts": {"target": 4, "action": 1},
                "false_positive_entity_counts": {"target": 3, "constraint": 8},
            },
            source_paths={"evaluation": "eval.json", "error_analysis": "errors.json"},
        )

        priorities = plan["field_priorities"]
        self.assertEqual(priorities[0]["field"], "constraint")
        self.assertEqual(priorities[0]["heuristic_requested_new_records"], 8)
        self.assertEqual(priorities[1]["field"], "target")
        self.assertEqual(plan["split_policy"]["targeted_followup_records"], "train_or_validation_only")
        self.assertTrue(plan["split_policy"]["fresh_test_set_needed"])

    def test_markdown_does_not_generate_command_text(self) -> None:
        plan = build_week2_collection_plan(
            span_summary={"records": 1, "span_field_counts": {"target": 1}},
            evaluation_summary={"records": 1, "entity_f1": 0.25},
            error_analysis={
                "false_negative_entity_counts": {"target": 1},
                "false_positive_entity_counts": {},
            },
            source_paths={},
        )

        markdown = render_week2_collection_plan_markdown(plan)

        self.assertIn("does not contain generated command text", markdown)
        self.assertIn("human-written span records", markdown)
        self.assertNotIn('"Send', markdown)


if __name__ == "__main__":
    unittest.main()
