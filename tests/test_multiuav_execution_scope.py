import unittest

from shepherd_ai.multiuav_execution_scope import execution_scope_contract


class MultiUavExecutionScopeTests(unittest.TestCase):
    def test_primary_scope_is_static_and_prohibits_execution_claims(self) -> None:
        contract = execution_scope_contract()

        self.assertEqual(contract["primary_scope"], "static_plan_fidelity")
        self.assertFalse(contract["official_server_submission_in_primary_scope"])
        self.assertFalse(contract["live_simulator_execution_in_primary_scope"])
        self.assertIn("official_command_fidelity", contract["primary_fidelity_metrics"])
        self.assertIn("live mission success", contract["prohibited_claims"])


if __name__ == "__main__":
    unittest.main()
