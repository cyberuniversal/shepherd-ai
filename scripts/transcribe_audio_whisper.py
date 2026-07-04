"""Transcribe Week 2 WAV commands with Whisper and evaluate transcripts."""

from __future__ import annotations

import argparse
from importlib import metadata
import json
from pathlib import Path
import platform
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.audio_manifest import evaluate_transcripts, load_audio_manifest  # noqa: E402
from shepherd_ai.whisper_asr import (  # noqa: E402
    build_whisper_prediction,
    prediction_transcript_map,
    require_device_substring,
    write_whisper_predictions,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Audio manifest JSONL.")
    parser.add_argument("--dataset-root", default=".", help="Root that audio paths must stay within.")
    parser.add_argument("--predictions-output", required=True, help="JSONL output for raw Whisper predictions.")
    parser.add_argument("--evaluation-output", required=True, help="JSON output for transcript evaluation.")
    parser.add_argument("--model", default="base", help="Whisper model name, for example tiny, base, small.")
    parser.add_argument("--device", default="cuda", help="Whisper device, usually cuda in Colab.")
    parser.add_argument("--language", default=None, help="Optional language code, for example en.")
    parser.add_argument("--fp16", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--required-device-substring",
        default=None,
        help="Require a CUDA device name containing this substring, for example T4.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_audio_manifest(args.manifest, dataset_root=args.dataset_root)
    device_metadata = require_device_substring(args.required_device_substring)

    try:
        import whisper
    except ImportError as exc:
        raise RuntimeError(
            "Whisper is not installed. In Colab, run: python -m pip install -q openai-whisper"
        ) from exc

    import torch

    model = whisper.load_model(args.model, device=args.device)
    parameters: dict[str, Any] = {
        "manifest": args.manifest,
        "dataset_root": args.dataset_root,
        "model": args.model,
        "device": args.device,
        "language": args.language,
        "fp16": args.fp16,
        "device_metadata": device_metadata,
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
        },
        "packages": {
            "openai-whisper": _package_version("openai-whisper"),
            "torch": getattr(torch, "__version__", "not stated"),
        },
    }
    predictions = []
    for record in records:
        transcription_args: dict[str, Any] = {"fp16": args.fp16}
        if args.language:
            transcription_args["language"] = args.language
        result = model.transcribe(str(record.audio_path), **transcription_args)
        predictions.append(
            build_whisper_prediction(
                record,
                predicted_transcript=str(result.get("text", "")),
                model_name="whisper",
                model_version=args.model,
                parameters={
                    **parameters,
                    "segments": len(result.get("segments", [])),
                    "detected_language": result.get("language"),
                },
            )
        )

    write_whisper_predictions(args.predictions_output, predictions)

    expected = {record.id: record.transcript for record in records}
    evaluation = evaluate_transcripts(
        expected,
        prediction_transcript_map(predictions),
        model_name="whisper",
        model_version=args.model,
        parameters=parameters,
    )
    evaluation_output = Path(args.evaluation_output)
    evaluation_output.parent.mkdir(parents=True, exist_ok=True)
    evaluation_output.write_text(json.dumps(evaluation, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(evaluation["summary"], indent=2, sort_keys=True))


def _package_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "not installed"


if __name__ == "__main__":
    main()
