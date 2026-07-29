import json
import unittest

from shepherd_ai.multiuav_plan_contract import parse_strict_model_output


def _render(payload: dict) -> str:
    return json.dumps(payload)


class MultiUavPlanContractTests(unittest.TestCase):
    def test_execute_requires_nonempty_source_shaped_api_plan(self) -> None:
        raw = _render(
            {
                "decision": "EXECUTE",
                "reason": "The requested drone and altitude are visible.",
                "clarification_question": None,
                "api_plan": [
                    {
                        "endpoint": "/drones/{id}/command/take_off",
                        "parameters": {"id": "drone-1", "altitude": 20},
                    }
                ],
            }
        )

        result = parse_strict_model_output(raw)

        self.assertEqual(result.parse_status, "PARSED")
        self.assertEqual(result.parsed.decision, "EXECUTE")
        self.assertEqual(
            result.parsed.api_plan[0].endpoint,
            "/drones/{id}/command/take_off",
        )

    def test_clarify_requires_question_and_empty_plan(self) -> None:
        result = parse_strict_model_output(
            _render(
                {
                    "decision": "CLARIFY",
                    "reason": "The required UAV identity is missing.",
                    "clarification_question": "Which UAV should execute the mission?",
                    "api_plan": [],
                }
            )
        )

        self.assertEqual(result.parse_status, "PARSED")
        self.assertEqual(result.parsed.decision, "CLARIFY")

    def test_block_requires_no_question_and_empty_plan(self) -> None:
        result = parse_strict_model_output(
            _render(
                {
                    "decision": "BLOCK",
                    "reason": "No registered UAV can satisfy the request.",
                    "clarification_question": None,
                    "api_plan": [],
                }
            )
        )

        self.assertEqual(result.parse_status, "PARSED")
        self.assertEqual(result.parsed.decision, "BLOCK")

    def test_empty_execute_plan_is_preserved_as_parse_error(self) -> None:
        raw = _render(
            {
                "decision": "EXECUTE",
                "reason": "Proceed.",
                "clarification_question": None,
                "api_plan": [],
            }
        )

        result = parse_strict_model_output(raw)

        self.assertEqual(result.parse_status, "PARSE_ERROR")
        self.assertEqual(result.error_code, "empty_execute_plan")
        self.assertEqual(result.raw_output, raw)
        self.assertIsNone(result.parsed)

    def test_malformed_or_fenced_output_is_not_repaired(self) -> None:
        malformed = '{"decision": "EXECUTE"'
        fenced = "```json\n{}\n```"

        malformed_result = parse_strict_model_output(malformed)
        fenced_result = parse_strict_model_output(fenced)

        self.assertEqual(malformed_result.error_code, "invalid_json")
        self.assertEqual(fenced_result.error_code, "invalid_json")

    def test_duplicate_keys_and_lowercase_decision_are_rejected(self) -> None:
        duplicate = (
            '{"decision":"BLOCK","decision":"EXECUTE","reason":"x",'
            '"clarification_question":null,"api_plan":[]}'
        )
        lowercase = _render(
            {
                "decision": "execute",
                "reason": "Proceed.",
                "clarification_question": None,
                "api_plan": [],
            }
        )

        self.assertEqual(
            parse_strict_model_output(duplicate).error_code,
            "duplicate_json_key",
        )
        self.assertEqual(
            parse_strict_model_output(lowercase).error_code,
            "invalid_decision",
        )
        wrong_type = json.loads(lowercase)
        wrong_type["decision"] = ["EXECUTE"]
        self.assertEqual(
            parse_strict_model_output(_render(wrong_type)).error_code,
            "invalid_decision",
        )

    def test_unknown_fields_and_empty_parameter_references_are_rejected(self) -> None:
        extra_field = {
            "decision": "BLOCK",
            "reason": "No resources.",
            "clarification_question": None,
            "api_plan": [],
            "confidence": 0.9,
        }
        empty_reference = {
            "decision": "EXECUTE",
            "reason": "Proceed.",
            "clarification_question": None,
            "api_plan": [
                {
                    "endpoint": "/drones/{id}/command/take_off",
                    "parameters": {"id": ""},
                }
            ],
        }

        self.assertEqual(
            parse_strict_model_output(_render(extra_field)).error_code,
            "output_schema_mismatch",
        )
        self.assertEqual(
            parse_strict_model_output(_render(empty_reference)).error_code,
            "empty_parameter_value",
        )


if __name__ == "__main__":
    unittest.main()
