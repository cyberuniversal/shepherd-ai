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
        configs_exist = (
            ROOT / "datasets" / "multiuav_plat" / "accuracy_run_configs_v1.json"
        ).is_file()
        excluded_attempt_exists = (
            ROOT
            / "datasets"
            / "multiuav_plat"
            / "failed_attempts"
            / "qwen25_3b_local_accuracy_attempt1_summary.json"
        ).is_file()

        self.assertTrue(result["valid"])
        self.assertEqual(result["primary_path"]["input_modality"], "text")
        self.assertFalse(result["runtime_invocation"]["whisper_invoked"])
        self.assertFalse(result["runtime_invocation"]["distilbert_invoked"])
        self.assertFalse(
            result["runtime_invocation"]["legacy_week8_pipeline_invoked"]
        )
        self.assertTrue(result["runtime_invocation"]["qwen_invoked"])
        self.assertEqual(
            result["runtime_invocation"]["qwen_invocation_scope"],
            (
                "synthetic_fixture_and_excluded_local_feasibility_attempt"
                if excluded_attempt_exists
                else "synthetic_fixture_only"
            ),
        )
        self.assertEqual(
            result["runtime_invocation"]["qwen_study_cases_evaluated"],
            excluded_attempt_exists,
        )
        self.assertEqual(
            result["runtime_invocation"]["qwen_study_rows_evaluated"],
            1 if excluded_attempt_exists else 0,
        )
        self.assertEqual(result["ready_for_model_inference"], configs_exist)
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
        self.assertFalse(result["ready_for_human_review"])
        self.assertTrue(result["expert_qc_complete"])
        self.assertTrue(result["ready_for_accuracy_run_config_binding"])
        self.assertEqual(
            result["status"],
            (
                "ready_for_accuracy_model_inference"
                if configs_exist
                else "accuracy_manifest_approved_final_commit_binding_pending"
            ),
        )
        self.assertEqual(
            result["primary_path"]["dataset"],
            "approved_test_manifest_284_clusters_1420_cases",
        )
        self.assertIn(
            "training_pilot_deterministic_validation",
            result["completed_gates"],
        )
        self.assertNotIn(
            "reviewer_identity_and_independence_attestation",
            result["blocking_gates"],
        )
        self.assertIn(
            "training_pilot_structural_review_validation",
            result["completed_gates"],
        )
        self.assertIn(
            "full_intervention_dataset_generation_and_deterministic_validation",
            result["completed_gates"],
        )
        self.assertNotIn(
            "full_intervention_dataset_review",
            result["blocking_gates"],
        )
        self.assertIn(
            "stratified_expert_construction_qc",
            result["completed_gates"],
        )
        self.assertIn(
            "score_blind_accuracy_protocol_registration",
            result["completed_gates"],
        )
        self.assertIn(
            "heldout_accuracy_case_manifest_approval",
            result["completed_gates"],
        )
        self.assertEqual(
            result["accuracy_blocking_gates"],
            [] if configs_exist else ["final_accuracy_run_config_commit_binding"],
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
        self.assertIn(
            "local_qwen_backend_and_process_socket_isolation_contract",
            result["completed_gates"],
        )
        self.assertNotIn(
            "offline_inference_isolation",
            result["blocking_gates"],
        )
        self.assertIn(
            "qwen_3b_cached_checksums_and_synthetic_load_smoke",
            result["completed_gates"],
        )
        self.assertIn(
            "qwen_7b_cached_checksums_and_synthetic_load_smoke",
            result["completed_gates"],
        )
        self.assertNotIn(
            "qwen_7b_cache_checksums_and_synthetic_load_smoke",
            result["blocking_gates"],
        )
        self.assertNotIn("m1_to_m4_call_budget", result["blocking_gates"])
        self.assertNotIn("strict_api_plan_contract", result["blocking_gates"])
        self.assertIn(
            "static_plan_fidelity_execution_scope",
            result["completed_gates"],
        )
        self.assertIn(
            "method_case_hardware_measurement_instrumentation",
            result["completed_gates"],
        )
        self.assertIn(
            "resource_candidate_subset_and_condition_order",
            result["completed_gates"],
        )
        self.assertIn(
            "resource_run_config_builder_with_approval_gate",
            result["completed_gates"],
        )
        self.assertIn(
            "publication_accuracy_smoke_leak_gate",
            result["completed_gates"],
        )
        self.assertNotIn(
            "resource_subset_and_repetition_orchestration",
            result["blocking_gates"],
        )
        self.assertIn(
            "resource_run_configs_commit_binding",
            result["blocking_gates"],
        )
        self.assertNotIn("execution_scope", result["blocking_gates"])
        self.assertNotIn(
            "hardware_warmup_and_thermal_controls", result["blocking_gates"]
        )
        self.assertIn("resource_cluster_preflight", result["blocking_gates"])
        self.assertIn(
            "resource_approved_subset_and_case_order",
            result["completed_gates"],
        )
        self.assertIn(
            "resource_hardware_warmup_thermal_and_process_controls",
            result["completed_gates"],
        )
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
            result["artifact_bindings"][
                "intervention_validator_negative_controls"
            ]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["intervention_pilot_review_packet"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"][
                "completed_intervention_pilot_review_packet"
            ]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"][
                "completed_intervention_pilot_review_validation"
            ]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"][
                "intervention_pilot_review_normalization"
            ]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["intervention_dataset"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["intervention_dataset_summary"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["intervention_dataset_validation"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["intervention_review_packet"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["expert_qc_audit"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["accuracy_protocol_freeze"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["accuracy_case_manifest"]["exists"]
        )
        self.assertEqual(
            result["artifact_bindings"]["accuracy_run_configs"]["exists"],
            configs_exist,
        )
        self.assertEqual(
            result["artifact_bindings"][
                "excluded_local_accuracy_attempt_summary"
            ]["exists"],
            excluded_attempt_exists,
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
        self.assertTrue(
            result["artifact_bindings"][
                "offline_runtime_contract_audit"
            ]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["qwen_3b_cache_audit"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["qwen_3b_load_smoke"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["qwen_3b_failed_load_smoke"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["qwen_3b_historical_load_smoke"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["qwen_7b_cache_audit"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["qwen_7b_load_smoke"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["execution_scope_audit"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"][
                "hardware_measurement_contract_audit"
            ]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["resource_schedule_candidate"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["resource_hardware_protocol"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["resource_final_schedule"]["exists"]
        )
        self.assertEqual(
            result["artifact_bindings"]["source_audit"]["path"],
            "datasets/multiuav_plat/source_audit_v1.json",
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
        configs_exist = (
            ROOT / "datasets" / "multiuav_plat" / "accuracy_run_configs_v1.json"
        ).is_file()
        self.assertEqual(
            result["claim_status"],
            (
                "accuracy_execution_ready_after_excluded_local_feasibility_attempt"
                if configs_exist
                and (
                    ROOT
                    / "datasets"
                    / "multiuav_plat"
                    / "failed_attempts"
                    / "qwen25_3b_local_accuracy_attempt1_summary.json"
                ).is_file()
                else "accuracy_execution_ready_no_study_inference"
                if configs_exist
                else "expert_qc_protocol_manifest_and_scoring_contract_complete_"
                "final_commit_binding_pending"
            ),
        )


if __name__ == "__main__":
    unittest.main()
