import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_audio_manifest_from_packet.py"


class BuildAudioManifestFromPacketCliTests(unittest.TestCase):
    def test_cli_builds_manifest_from_ready_packet_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio_dir = root / "datasets" / "sample_audio"
            audio_dir.mkdir(parents=True)
            (audio_dir / "audio_postdev_001.wav").write_bytes(b"RIFF")
            packet = root / "packet.jsonl"
            packet.write_text(json.dumps(_row()) + "\n", encoding="utf-8")
            manifest = root / "manifest.jsonl"
            summary = root / "summary.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--packet",
                    str(packet),
                    "--dataset-root",
                    str(root),
                    "--manifest-output",
                    str(manifest),
                    "--summary-output",
                    str(summary),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
            payload = json.loads(summary.read_text(encoding="utf-8"))

        self.assertIn('"records": 1', completed.stdout)
        self.assertEqual(rows[0]["id"], "audio_postdev_001")
        self.assertEqual(rows[0]["transcript"], "Inspect the nursery rows after sunrise.")
        self.assertEqual(payload["summary"]["split_counts"], {"validation": 1})

    def test_cli_rejects_blank_packet_rows_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet = root / "packet.jsonl"
            row = _row()
            row["transcript"] = ""
            row["collection_status"] = "blank_slot_not_collected"
            packet.write_text(json.dumps(row) + "\n", encoding="utf-8")
            manifest = root / "manifest.jsonl"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--packet",
                    str(packet),
                    "--dataset-root",
                    str(root),
                    "--manifest-output",
                    str(manifest),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("packet has unready rows", completed.stderr)

    def test_cli_rejects_duplicate_transcripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio_dir = root / "datasets" / "sample_audio"
            audio_dir.mkdir(parents=True)
            (audio_dir / "audio_postdev_001.wav").write_bytes(b"RIFF")
            (audio_dir / "audio_postdev_002.wav").write_bytes(b"RIFF")
            first = _row()
            second = _row(record_id="audio_postdev_002")
            second["audio_path"] = "datasets/sample_audio/audio_postdev_002.wav"
            packet = root / "packet.jsonl"
            packet.write_text(json.dumps(first) + "\n" + json.dumps(second) + "\n", encoding="utf-8")
            manifest = root / "manifest.jsonl"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--packet",
                    str(packet),
                    "--dataset-root",
                    str(root),
                    "--manifest-output",
                    str(manifest),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("duplicate normalized transcript", completed.stderr)


def _row(record_id: str = "audio_postdev_001") -> dict:
    return {
        "slot_id": record_id,
        "id": record_id,
        "split": "validation",
        "audio_path": f"datasets/sample_audio/{record_id}.wav",
        "transcript": "Inspect the nursery rows after sunrise.",
        "source": "manual_week2_post_development_audio_v1",
        "data_type": "human_recorded_audio",
        "collection_status": "human_transcript_verified",
    }


if __name__ == "__main__":
    unittest.main()
