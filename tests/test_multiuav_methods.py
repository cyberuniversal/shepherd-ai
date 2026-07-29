import unittest

from shepherd_ai.multiuav_methods import (
    METHOD_SPECS,
    MethodSpec,
    validate_method_specs,
)


class MultiUavMethodTests(unittest.TestCase):
    def test_registered_call_budgets_match_the_code_plan(self) -> None:
        result = validate_method_specs()

        self.assertTrue(result["valid"])
        self.assertEqual(
            result["call_counts"],
            {
                "M1_monolithic": 1,
                "M2_post_plan_deterministic": 1,
                "M3_stage_wise": 2,
                "M4_post_plan_compute_matched": 2,
            },
        )

    def test_m3_m4_call_count_drift_is_rejected(self) -> None:
        changed = tuple(
            MethodSpec(
                method_id=spec.method_id,
                model_call_count=1,
                model_call_purposes=spec.model_call_purposes[:1],
                deterministic_preplan_gate=spec.deterministic_preplan_gate,
                deterministic_postplan_gate=spec.deterministic_postplan_gate,
                learned_postplan_validator=spec.learned_postplan_validator,
            )
            if spec.method_id == "M4_post_plan_compute_matched"
            else spec
            for spec in METHOD_SPECS
        )

        with self.assertRaisesRegex(ValueError, "M4 must use two"):
            validate_method_specs(changed)


if __name__ == "__main__":
    unittest.main()
