import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "import_hf_checkpoint.py"


class ImportHfCheckpointCliTests(unittest.TestCase):
    def test_cli_imports_packaged_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "checkpoint.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("hf_model/config.json", "{}")
                zf.writestr("hf_model/model.safetensors", b"weights")
                zf.writestr("hf_model/tokenizer.json", "{}")
            output_dir = root / "outputs" / "model_artifacts"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--checkpoint-zip",
                    str(archive),
                    "--output-dir",
                    str(output_dir),
                    "--expected-name",
                    "hf_model",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            result = json.loads(completed.stdout)
            installed = output_dir / "hf_model"

            self.assertTrue((installed / "config.json").is_file())
            self.assertTrue((installed / "model.safetensors").is_file())
            self.assertTrue((installed / "tokenizer.json").is_file())
            self.assertTrue((installed / "local_import_manifest.json").is_file())
            self.assertEqual(result["installed_dir"], str(installed.resolve()))

    def test_cli_rejects_notebook_export_zip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "notebook.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("Notebook2_NLP_Colab_T4.ipynb", "{}")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--checkpoint-zip",
                    str(archive),
                    "--output-dir",
                    str(root / "models"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("could not find a single valid checkpoint folder", completed.stderr)


if __name__ == "__main__":
    unittest.main()
