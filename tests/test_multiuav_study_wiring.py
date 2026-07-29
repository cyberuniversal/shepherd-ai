import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from shepherd_ai.multiuav_study_wiring import audit_primary_study_wiring


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_multiuav_study_wiring.py"


class MultiUavStudyWiringTests(unittest.TestCase):
    def test_primary_path_excludes_legacy_nlp_and_reports_blockers(self) -> None:
        result = audit_primary_study_wiring(ROOT)

        self.assertTrue(result["valid"])
        self.assertEqual(result["primary_path"]["input_modality"], "text")
        self.assertFalse(result["runtime_invocation"]["whisper_invoked"])
        self.assertFalse(result["runtime_invocation"]["distilbert_invoked"])
        self.assertFalse(
            result["runtime_invocation"]["legacy_week8_pipeline_invoked"]
        )
        self.assertFalse(result["runtime_invocation"]["qwen_invoked"])
        self.assertFalse(result["ready_for_model_inference"])
        self.assertNotIn(
            "agent_visible_context_projection",
            result["blocking_gates"],
        )
        self.assertIn(
            "agent_visible_context_projection",
            result["completed_gates"],
        )
        self.assertNotIn("recoverability_rule", result["blocking_gates"])
        self.assertIn("recoverability_rule", result["completed_gates"])
        self.assertTrue(result["ready_for_intervention_generation"])
        self.assertTrue(result["ready_for_human_review"])
        self.assertEqual(
            result["status"],
            "training_pilot_ready_for_human_review",
        )
        self.assertEqual(
            result["primary_path"]["dataset"],
            "training_pilot_30_clusters_pending_human_review",
        )
        self.assertIn(
            "training_pilot_deterministic_validation",
            result["completed_gates"],
        )
        self.assertIn(
            "human_intervention_review_and_adjudication",
            result["blocking_gates"],
        )
        self.assertIn("method_call_budget", result["completed_gates"])
        self.assertIn(
            "strict_structural_output_contract",
            result["completed_gates"],
        )
        self.assertIn(
            "deterministic_recursive_grounding_validator",
            result["completed_gates"],
        )
        self.assertNotIn(
            "deterministic_recursive_validator",
            result["blocking_gates"],
        )
        self.assertIn(
            "immutable_qwen_checkpoint_resolution",
            result["completed_gates"],
        )
        self.assertNotIn(
            "immutable_qwen_checkpoint_resolution",
            result["blocking_gates"],
        )
        self.assertIn(
            "method_runners_and_prompts",
            result["completed_gates"],
        )
        self.assertIn(
            "row_checkpoint_resume_contract",
            result["completed_gates"],
        )
        self.assertNotIn(
            "method_runners_and_prompts",
            result["blocking_gates"],
        )
        self.assertNotIn("m1_to_m4_call_budget", result["blocking_gates"])
        self.assertNotIn("strict_api_plan_contract", result["blocking_gates"])
        self.assertEqual(
            result["primary_path"]["api_plan_parser"],
            "strict_multiuav_json_contract_v1",
        )
        self.assertTrue(
            result["artifact_bindings"]["agent_context_audit"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["recoverability_audit"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["intervention_pilot"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["intervention_pilot_validation"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["intervention_pilot_review_packet"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["method_contract_audit"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["grounding_contract_audit"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["model_revision_audit"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["runner_contract_audit"]["exists"]
        )
        self.assertEqual(
            result["primary_path"]["deterministic_validator"],
            "recursive_visible_evidence_grounding_v1",
        )
        self.assertTrue(
            result["artifact_bindings"][
                "historical_distilbert_wiring_smoke"
            ]["exists"]
        )
        self.assertIn(
            "wired and smoke-tested",
            result["legacy_component_roles"]["distilbert_week2_span_tagger"],
        )

    def test_missing_completed_gate_makes_wiring_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = audit_primary_study_wiring(Path(temp_dir))

        self.assertFalse(result["valid"])
        self.assertEqual(result["status"], "invalid_completed_gate_wiring")
        self.assertTrue(
            any("missing wiring artifact" in error for error in result["errors"])
        )

    def test_cli_preserves_audit_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "wiring.json"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repository-root",
                    str(ROOT),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(output.read_text(encoding="utf-8"))

        self.assertTrue(result["valid"])
        self.assertEqual(
            result["claim_status"],
            (
                "unreviewed_training_pilot_runner_checkpoint_and_model_"
                "revisions_wired_no_revised_inference"
            ),
        )


if __name__ == "__main__":
    unittest.main()
