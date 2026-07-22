"""Register one human-recorded WAV for the fixed Week 8 scenario."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import wave


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week8_completion import ROADMAP_COMMAND  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wav", type=Path, required=True)
    parser.add_argument(
        "--staged-wav",
        type=Path,
        default=ROOT / "datasets/sample_audio/week8_exact_scenario.wav",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        default=ROOT / "datasets/sample_audio/week8_exact_scenario_manifest.jsonl",
    )
    args = parser.parse_args()
    if not args.wav.is_file() or args.wav.suffix.lower() != ".wav":
        raise SystemExit("--wav must point to an existing .wav file")
    try:
        with wave.open(str(args.wav), "rb") as handle:
            metadata = {
                "channels": handle.getnchannels(),
                "sample_width_bytes": handle.getsampwidth(),
                "sample_rate_hz": handle.getframerate(),
                "frames": handle.getnframes(),
            }
    except wave.Error as exc:
        raise SystemExit(f"--wav must be a readable PCM WAV file: {exc}") from exc
    args.staged_wav.parent.mkdir(parents=True, exist_ok=True)
    if args.wav.resolve() != args.staged_wav.resolve():
        shutil.copyfile(args.wav, args.staged_wav)
    record = {
        "id": "week8_exact_scenario_audio",
        "audio_path": _repo_path(args.staged_wav),
        "transcript": ROADMAP_COMMAND,
        "split": "scenario_evaluation",
        "source": "human_recorded_for_roadmap_week8_fixed_scenario",
        "data_type": "human_recorded_audio",
        "audio_metadata": metadata,
    }
    args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_output.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


if __name__ == "__main__":
    main()
