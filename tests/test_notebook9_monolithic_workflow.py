import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "Notebook9_Evaluation.ipynb"


class Notebook9ActiveStudyWorkflowTests(unittest.TestCase):
    def test_notebook_uses_active_multiuav_branch_and_completed_gates(self) -> None:
        notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        source = "\n".join(
            "".join(cell.get("source", [])) for cell in notebook["cells"]
        )

        self.assertIn("codex/multiuav-validation-study", source)
        self.assertIn("audit_primary_study_wiring", source)
        self.assertIn("audit_multiuav_plat_source.py", source)
        self.assertIn("build_multiuav_session_split.py", source)
        self.assertIn("build_multiuav_task_eligibility.py", source)
        self.assertIn("RUN_SOURCE_REAUDIT = False", source)
        setup_cell = "".join(notebook["cells"][1].get("source", []))
        self.assertIn("%pip install -q -e .", setup_cell)
        self.assertIn("'pull', '--ff-only'", setup_cell)
        self.assertIn("sys.path.insert(0, src_path)", setup_cell)
        self.assertLess(
            setup_cell.index("%pip install -q -e ."),
            setup_cell.index("sys.path.insert(0, src_path)"),
        )

    def test_notebook_does_not_invoke_superseded_model_paths(self) -> None:
        notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        source = "\n".join(
            "".join(cell.get("source", [])) for cell in notebook["cells"]
        )

        self.assertNotIn("run_hf_monolithic_decision_baseline.py", source)
        self.assertNotIn("build_monolithic_decision_packet.py", source)
        self.assertNotIn("evaluate_evidence_aware_decisions.py", source)
        self.assertNotIn("hf_token_classifier", source)
        self.assertIn("ready_for_model_inference'] is False", source)


if __name__ == "__main__":
    unittest.main()
