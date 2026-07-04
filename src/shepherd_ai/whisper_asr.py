"""Helpers for Whisper transcript inference artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from shepherd_ai.audio_manifest import AudioManifestRecord


@dataclass(frozen=True)
class WhisperPrediction:
    id: str
    audio_path: str
    expected_transcript: str
    predicted_transcript: str
    model_name: str
    model_version: str
    parameters: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "audio_path": self.audio_path,
            "expected_transcript": self.expected_transcript,
            "predicted_transcript": self.predicted_transcript,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "parameters": self.parameters,
        }


def build_whisper_prediction(
    record: AudioManifestRecord,
    *,
    predicted_transcript: str,
    model_name: str,
    model_version: str,
    parameters: dict[str, Any],
) -> WhisperPrediction:
    """Create one serializable Whisper prediction row."""

    return WhisperPrediction(
        id=record.id,
        audio_path=str(record.audio_path),
        expected_transcript=record.transcript,
        predicted_transcript=predicted_transcript.strip(),
        model_name=model_name,
        model_version=model_version,
        parameters=parameters,
    )


def write_whisper_predictions(path: str | Path, predictions: list[WhisperPrediction]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(prediction.to_dict(), sort_keys=True) + "\n" for prediction in predictions),
        encoding="utf-8",
    )


def load_whisper_predictions(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def prediction_transcript_map(predictions: list[WhisperPrediction] | list[dict[str, Any]]) -> dict[str, str]:
    """Return `{record_id: predicted_transcript}` from prediction rows."""

    rows: dict[str, str] = {}
    for prediction in predictions:
        if isinstance(prediction, WhisperPrediction):
            rows[prediction.id] = prediction.predicted_transcript
        else:
            rows[str(prediction["id"])] = str(prediction.get("predicted_transcript", ""))
    return rows


def require_device_substring(required_substring: str | None, torch_module: Any | None = None) -> dict[str, Any]:
    """Validate that CUDA device names contain the required substring.

    Returns runtime metadata so callers can persist the actual device state.
    """

    if torch_module is None:
        import torch as torch_module  # type: ignore[no-redef]

    cuda_available = bool(torch_module.cuda.is_available())
    device_names = (
        [str(torch_module.cuda.get_device_name(index)) for index in range(torch_module.cuda.device_count())]
        if cuda_available
        else []
    )
    metadata = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "cuda_available": cuda_available,
        "cuda_device_names": device_names,
        "required_device_substring": required_substring,
    }
    if required_substring and not any(required_substring in name for name in device_names):
        raise RuntimeError(
            f"required device substring {required_substring!r} not found in CUDA devices: {device_names}"
        )
    return metadata
