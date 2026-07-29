import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_context import (  # noqa: E402
    PRIVILEGED_SOURCE_FIELDS,
    project_agent_visible_context,
)
from shepherd_ai.multiuav_interventions import (  # noqa: E402
    materialize_case_context,
)
from shepherd_ai.multiuav_prompts import (  # noqa: E402
    EVIDENCE_LEDGER_SCHEMA,
    FINAL_OUTPUT_SCHEMA,
    PROMPT_CONTRACT_VERSION,
    build_first_call_request,
    build_second_call_request,
    prompt_template_audit,
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
            "environment": {
                "id": "environment-1",
                "name": "Clear",
                "weather": "clear",
            },
        },
        task_id="task-1",
        instruction="Have Drone 1 take off to 20 meters.",
    )


def _find_keys(value, forbidden) -> set[str]:
    found = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in forbidden:
                found.add(key)
            found.update(_find_keys(child, forbidden))
    elif isinstance(value, list):
        for child in value:
            found.update(_find_keys(child, forbidden))
    return found


class MultiUavPromptTests(unittest.TestCase):
    def test_m1_m2_and_m4_first_call_prompts_are_byte_equivalent(self) -> None:
        requests = [
            build_first_call_request(method_id, _context())
            for method_id in (
                "M1_monolithic",
                "M2_post_plan_deterministic",
                "M4_post_plan_compute_matched",
            )
        ]

        self.assertEqual({item.request_sha256 for item in requests}, {
            requests[0].request_sha256
        })
        self.assertTrue(
            all(item.response_contract == FINAL_OUTPUT_SCHEMA for item in requests)
        )

    def test_m3_first_call_uses_evidence_ledger_contract(self) -> None:
        request = build_first_call_request("M3_stage_wise", _context())

        self.assertEqual(request.call_index, 0)
        self.assertEqual(request.response_contract, EVIDENCE_LEDGER_SCHEMA)
        self.assertIn("evidence ledger", request.messages[0].content)
        self.assertEqual(
            json.loads(request.messages[1].content)["RESPONSE_CONTRACT"],
            EVIDENCE_LEDGER_SCHEMA,
        )

    def test_second_call_contracts_are_method_specific(self) -> None:
        m3 = build_second_call_request(
            "M3_stage_wise",
            _context(),
            first_raw_output='{"provisional_decision":"EXECUTE"}',
            preplan_report={"valid": False, "issues": ["fixture"]},
        )
        m4 = build_second_call_request(
            "M4_post_plan_compute_matched",
            _context(),
            first_raw_output='{"decision":"EXECUTE"}',
        )

        self.assertEqual(m3.call_index, 1)
        self.assertEqual(m4.call_index, 1)
        self.assertEqual(m3.response_contract, FINAL_OUTPUT_SCHEMA)
        self.assertEqual(m4.response_contract, FINAL_OUTPUT_SCHEMA)
        self.assertIn(
            "DETERMINISTIC_PREPLAN_REPORT",
            json.loads(m3.messages[1].content),
        )
        self.assertIn(
            "FIRST_CALL_CANDIDATE_RAW",
            json.loads(m4.messages[1].content),
        )

    def test_one_call_methods_reject_second_call_construction(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not have a second"):
            build_second_call_request(
                "M1_monolithic",
                _context(),
                first_raw_output="{}",
            )

    def test_prompt_audit_excludes_hidden_reference_inputs(self) -> None:
        audit = prompt_template_audit()

        self.assertEqual(
            audit["prompt_contract_version"],
            PROMPT_CONTRACT_VERSION,
        )
        self.assertIn("related_apis", audit["excluded_inputs"])
        self.assertIn("execution_check_apis", audit["excluded_inputs"])
        self.assertNotIn("proposed_decision", audit["visible_inputs"])

    def test_all_pilot_first_prompts_preserve_only_materialized_context(
        self,
    ) -> None:
        pilot = json.loads(
            (
                ROOT
                / "datasets"
                / "multiuav_plat"
                / "intervention_pilot_v1.json"
            ).read_text(encoding="utf-8")
        )
        for cluster in pilot["clusters"]:
            for case in cluster["cases"]:
                context = materialize_case_context(cluster, case)
                for method_id in (
                    "M1_monolithic",
                    "M2_post_plan_deterministic",
                    "M3_stage_wise",
                    "M4_post_plan_compute_matched",
                ):
                    request = build_first_call_request(method_id, context)
                    payload = json.loads(request.messages[1].content)
                    self.assertEqual(payload["AGENT_CONTEXT"], context)
                    self.assertFalse(
                        _find_keys(payload, PRIVILEGED_SOURCE_FIELDS)
                    )
                    self.assertNotIn("proposed_decision", payload)
                    self.assertNotIn("label_status", payload)


if __name__ == "__main__":
    unittest.main()
