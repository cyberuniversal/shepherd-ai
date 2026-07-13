import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "package_week6_cpu_artifacts.py"
ARTIFACTS = (
    "datasets/aerial_images/manifest.jsonl",
    "outputs/evaluations/week6_agriculture_vision_cache_provenance.json",
    "outputs/evaluations/week6_agriculture_vision_layout.json",
    "outputs/evaluations/week6_vision_manifest_summary.json",
    "outputs/evaluations/week6_agriculture_vision_label_audit.json",
)


class PackageWeek6CpuArtifactsCliTests(unittest.TestCase):
    def test_packages_only_non_image_research_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            for relative in ARTIFACTS:
                path = repo / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}\n", encoding="utf-8")
            output = repo / "week6_cpu_artifacts.zip"

            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--repo-root", str(repo), "--output-zip", str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            manifest = json.loads(completed.stdout)
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())

        self.assertFalse(manifest["contains_licensed_pixels"])
        self.assertFalse(manifest["contains_model_weights"])
        self.assertEqual(len(manifest["files"]), 5)
        self.assertEqual(names, set(ARTIFACTS) | {"week6_cpu_artifact_manifest.json"})
        self.assertTrue(all(len(record["sha256"]) == 64 for record in manifest["files"]))

    def test_fails_when_an_artifact_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--repo-root", tmp, "--output-zip", str(Path(tmp) / "out.zip")],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("missing Week 6 CPU artifacts", completed.stderr)


if __name__ == "__main__":
    unittest.main()
