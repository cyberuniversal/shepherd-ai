import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_context import project_agent_visible_context  # noqa: E402
from shepherd_ai.multiuav_runner import (  # noqa: E402
    GenerationResult,
    run_method_case,
)


def _context() -> dict:
    return project_agent_visible_context(
        {
            "id": "session-1",
            "task_type": "area_search",
            "canvas_width": 100,
            "canvas_height": 80,
            "is_distance_3d": True,
            "status": "active",
            "drones": [
                {
                    "id": "drone-1",
                    "name": "Drone 1",
                    "status": "idle",
                    "position": {"x": 0, "y": 0, "z": 0},
                    "heading": 0,
                    "max_altitude": 50,
                }
            ],
            "environment": {"id": "env-1", "weather": "clear"},
        },
        task_id="task-1",
        instruction="Have Drone 1 take off to 20 meters.",
    )


def _final_output(altitude: int = 20) -> str:
    return json.dumps(
        {
            "decision": "EXECUTE",
            "reason": "The required drone and altitude are visible.",
            "clarification_question": None,
            "api_plan": [
                {
                    "endpoint": "/drones/{id}/command/take_off",
                    "parameters": {"id": "drone-1", "altitude": altitude},
                }
            ],
        }
    )


def _ledger() -> str:
    return json.dumps(
        {
            "evidence": [
                {"source_path": "instruction", "claim": "Altitude is stated."},
                {"source_path": "drones[0].id", "claim": "Drone is visible."},
            ],
            "missing_operator_facts": [],
            "conflicts": [],
            "provisional_decision": "EXECUTE",
            "reason": "Evidence supports execution.",
        }
    )


class _ScriptedBackend:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        if not self.outputs:
            raise AssertionError("unexpected model call")
        return GenerationResult(
            raw_output=self.outputs.pop(0),
            input_tokens=10,
            output_tokens=5,
            latency_ms=1.5,
            metadata={"backend": "scripted_test_fixture"},
        )


class _FailingBackend:
    def generate(self, request):
        raise RuntimeError("synthetic backend failure")


class MultiUavRunnerTests(unittest.TestCase):
    def test_unreviewed_case_status_is_rejected_before_model_call(self) -> None:
        backend = _ScriptedBackend([_final_output()])

        with self.assertRaisesRegex(ValueError, "not approved"):
            run_method_case(
                case_id="case-1",
                case_status="pending_human_review",
                method_id="M1_monolithic",
                context=_context(),
                backend=backend,
            )

        self.assertEqual(backend.requests, [])

    def test_m1_uses_one_call_without_deterministic_postplan_gate(self) -> None:
        result = run_method_case(
            case_id="case-1",
            case_status="synthetic_unit_fixture",
            method_id="M1_monolithic",
            context=_context(),
            backend=_ScriptedBackend([_final_output(33)]),
        )

        self.assertEqual(result.actual_model_call_count, 1)
        self.assertEqual(result.final_parse["parse_status"], "PARSED")
        self.assertIsNone(result.deterministic_postplan_report)

    def test_m2_uses_one_call_and_contains_ungrounded_value(self) -> None:
        result = run_method_case(
            case_id="case-1",
            case_status="synthetic_unit_fixture",
            method_id="M2_post_plan_deterministic",
            context=_context(),
            backend=_ScriptedBackend([_final_output(33)]),
        )

        self.assertEqual(result.actual_model_call_count, 1)
        self.assertFalse(result.deterministic_postplan_report["valid"])
        self.assertEqual(
            result.deterministic_postplan_report["containment_stage"],
            "post_plan_parameter_grounding",
        )

    def test_m3_always_uses_second_call_after_invalid_ledger(self) -> None:
        backend = _ScriptedBackend(["not json", _final_output()])
        result = run_method_case(
            case_id="case-1",
            case_status="synthetic_unit_fixture",
            method_id="M3_stage_wise",
            context=_context(),
            backend=backend,
        )

        self.assertEqual(result.actual_model_call_count, 2)
        self.assertEqual(
            result.preplan_report["containment_stage"],
            "pre_plan_ledger_parse",
        )
        self.assertEqual(result.calls[0].generation.raw_output, "not json")

    def test_m4_uses_two_calls_and_scores_second_as_final(self) -> None:
        result = run_method_case(
            case_id="case-1",
            case_status="synthetic_unit_fixture",
            method_id="M4_post_plan_compute_matched",
            context=_context(),
            backend=_ScriptedBackend([_final_output(33), _final_output()]),
        )

        self.assertEqual(result.actual_model_call_count, 2)
        self.assertTrue(result.deterministic_postplan_report["valid"])
        self.assertEqual(
            result.final_parse["raw_output"],
            _final_output(),
        )

    def test_parse_error_raw_output_is_retained(self) -> None:
        result = run_method_case(
            case_id="case-1",
            case_status="synthetic_unit_fixture",
            method_id="M2_post_plan_deterministic",
            context=_context(),
            backend=_ScriptedBackend(["malformed"]),
        )

        self.assertEqual(result.final_parse["parse_status"], "PARSE_ERROR")
        self.assertEqual(result.final_parse["raw_output"], "malformed")
        self.assertIsNone(result.deterministic_postplan_report)

    def test_backend_error_becomes_retained_parse_error_row(self) -> None:
        result = run_method_case(
            case_id="case-1",
            case_status="synthetic_unit_fixture",
            method_id="M2_post_plan_deterministic",
            context=_context(),
            backend=_FailingBackend(),
        )

        self.assertEqual(
            result.calls[0].generation.generation_status,
            "BACKEND_ERROR",
        )
        self.assertEqual(
            result.calls[0].generation.error_type,
            "RuntimeError",
        )
        self.assertEqual(result.final_parse["parse_status"], "PARSE_ERROR")
        self.assertEqual(result.actual_model_call_count, 1)


if __name__ == "__main__":
    unittest.main()
