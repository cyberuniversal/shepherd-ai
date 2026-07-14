from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "train_agriculture_vision_segmentation.py"


class SegmentationCliTests(unittest.TestCase):
    def test_help_documents_reproducibility_controls_without_importing_torch(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("--seed", completed.stdout)
        self.assertIn("--resume", completed.stdout)
        self.assertIn("--required-device-substring", completed.stdout)
        self.assertIn("--device", completed.stdout)
        self.assertIn("--train-label-audit", completed.stdout)
        self.assertIn("--positive-weight-cap", completed.stdout)
        self.assertIn("--loss", completed.stdout)
        self.assertIn("--dice-weight", completed.stdout)


if __name__ == "__main__":
    unittest.main()
