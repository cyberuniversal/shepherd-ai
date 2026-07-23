import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "Notebook9_Evaluation.ipynb"


class Notebook9MonolithicWorkflowTests(unittest.TestCase):
    def test_notebook_uses_current_branch_and_keeps_gold_out_of_inference(self) -> None:
        notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        source = "\n".join(
            "".join(cell.get("source", [])) for cell in notebook["cells"]
        )

        self.assertIn("codex/evidence-aware-paper", source)
        self.assertIn("build_monolithic_decision_packet.py", source)
        self.assertIn("run_hf_monolithic_decision_baseline.py", source)
        self.assertIn("evaluate_monolithic_decision_baseline.py", source)
        setup_cell = "".join(notebook["cells"][1].get("source", []))
        self.assertIn("%pip install -q -e .", setup_cell)
        self.assertIn("'pull', '--ff-only'", setup_cell)
        self.assertIn("sys.path.insert(0, src_path)", setup_cell)
        self.assertLess(
            setup_cell.index("%pip install -q -e ."),
            setup_cell.index("sys.path.insert(0, src_path)"),
        )
        runner_cell = next(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if "run_hf_monolithic_decision_baseline.py"
            in "".join(cell.get("source", []))
        )
        self.assertNotIn("--gold", runner_cell)
        self.assertIn("--required-device-substring", runner_cell)
        self.assertIn("T4", runner_cell)


if __name__ == "__main__":
    unittest.main()
