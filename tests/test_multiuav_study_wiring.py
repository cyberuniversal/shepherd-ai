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
        self.assertTrue(
            result["artifact_bindings"]["agent_context_audit"]["exists"]
        )
        self.assertTrue(
            result["artifact_bindings"]["recoverability_audit"]["exists"]
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
        self.assertTrue(any("missing wiring artifact" in error for error in result["errors"]))

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
            "component_wiring_audited_no_revised_inference",
        )


if __name__ == "__main__":
    unittest.main()
