import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.monolithic_decision import (  # noqa: E402
    build_messages,
    messages_sha256,
    parse_model_response,
    validate_input_record,
)


class MonolithicDecisionTests(unittest.TestCase):
    def test_prompt_excludes_gold_fields(self) -> None:
        record = {
            "case_id": "case_001",
            "decision_stage": "grounding_sufficiency",
            "command": "Inspect the road.",
            "evidence": {"map_records": []},
            "expected_decision": "clarify",
        }

        messages = build_messages(record)
        rendered = "\n".join(message["content"] for message in messages)

        self.assertNotIn("expected_decision", rendered)
        self.assertNotIn('"clarify"', messages[1]["content"])

    def test_parses_strict_json_response(self) -> None:
        result = parse_model_response(
            '{"decision":"clarify","reason":"Two roads match.",'
            '"clarification_question":"Which road?"}'
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["decision"], "clarify")

    def test_accepts_json_code_fence_but_not_extra_prose(self) -> None:
        fenced = parse_model_response(
            "```json\n"
            '{"decision":"proceed","reason":"Evidence is sufficient.",'
            '"clarification_question":null}\n'
            "```"
        )
        prose = parse_model_response(
            'Answer: {"decision":"proceed","reason":"ok","clarification_question":null}'
        )

        self.assertTrue(fenced["valid"])
        self.assertFalse(prose["valid"])

    def test_requires_question_only_for_clarification(self) -> None:
        missing = parse_model_response(
            '{"decision":"clarify","reason":"Ambiguous.",'
            '"clarification_question":null}'
        )
        unexpected = parse_model_response(
            '{"decision":"block","reason":"Battery low.",'
            '"clarification_question":"Continue?"}'
        )

        self.assertFalse(missing["valid"])
        self.assertFalse(unexpected["valid"])

    def test_validates_prompt_hash_and_rejects_gold_in_input(self) -> None:
        base = {
            "case_id": "case_001",
            "decision_stage": "grounding_sufficiency",
            "command": "Inspect the road.",
            "evidence": {"map_records": []},
        }
        messages = build_messages(base)
        input_record = {
            **base,
            "messages": messages,
            "prompt_sha256": messages_sha256(messages),
        }
        validate_input_record(input_record)

        with self.assertRaisesRegex(ValueError, "contains gold fields"):
            validate_input_record({**input_record, "expected_decision": "clarify"})


if __name__ == "__main__":
    unittest.main()
