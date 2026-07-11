import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "package_hf_checkpoint.py"


class PackageHfCheckpointCliTests(unittest.TestCase):
    def test_cli_packages_checkpoint_with_manifest_and_includes_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_dir = root / "outputs" / "model_artifacts" / "hf_model"
            model_dir.mkdir(parents=True)
            (model_dir / "config.json").write_text("{}", encoding="utf-8")
            (model_dir / "model.safetensors").write_bytes(b"weights")
            (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
            metrics = root / "outputs" / "evaluations" / "metrics.json"
            metrics.parent.mkdir(parents=True)
            metrics.write_text('{"metric": 1}', encoding="utf-8")
            output_zip = root / "checkpoint.zip"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--model-dir",
                    str(model_dir),
                    "--output-zip",
                    str(output_zip),
                    "--include",
                    str(metrics),
                ],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )

            manifest = json.loads(completed.stdout)
            with zipfile.ZipFile(output_zip) as archive:
                names = set(archive.namelist())

        self.assertGreater(manifest["zip_size_bytes"], 0)
        self.assertIn("hf_model/config.json", names)
        self.assertIn("hf_model/model.safetensors", names)
        self.assertIn("hf_model/tokenizer.json", names)
        self.assertIn("hf_model/checkpoint_manifest.json", names)
        self.assertIn("outputs/evaluations/metrics.json", names)


if __name__ == "__main__":
    unittest.main()
