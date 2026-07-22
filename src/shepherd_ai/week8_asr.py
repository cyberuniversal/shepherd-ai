"""Exact-scenario ASR evidence assembly for Week 8."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from shepherd_ai.week8_completion import ROADMAP_COMMAND


def build_week8_asr_evidence(
    manifest_record: Mapping[str, Any],
    prediction_record: Mapping[str, Any],
    evaluation_record: Mapping[str, Any],
) -> dict[str, Any]:
    """Join one registered WAV, Whisper prediction, and transcript score."""

    if manifest_record.get("id") != "week8_exact_scenario_audio":
        raise ValueError("manifest must contain the fixed Week 8 audio id")
    if manifest_record.get("transcript") != ROADMAP_COMMAND:
        raise ValueError("manifest transcript must exactly match the roadmap command")
    if manifest_record.get("data_type") != "human_recorded_audio":
        raise ValueError("Week 8 ASR evidence requires human_recorded_audio")
    if prediction_record.get("id") != manifest_record.get("id"):
        raise ValueError("prediction id does not match manifest id")
    if evaluation_record.get("id") != manifest_record.get("id"):
        raise ValueError("evaluation id does not match manifest id")
    audio_path = Path(str(manifest_record.get("audio_path", "")))
    if not audio_path.is_file():
        raise FileNotFoundError(f"registered audio does not exist: {audio_path}")
    predicted = str(prediction_record.get("predicted_transcript", "")).strip()
    if not predicted:
        raise ValueError("Whisper prediction is empty")
    parameters = dict(prediction_record.get("parameters", {}))
    return {
        "scenario_source": "roadmap_week8_fixed_scenario",
        "reference_transcript": ROADMAP_COMMAND,
        "predicted_transcript": predicted,
        "audio": {
            "path": str(audio_path).replace("\\", "/"),
            "sha256": _sha256(audio_path),
            "data_type": "human_recorded_audio",
            "source": manifest_record.get("source", "not stated"),
            "split": manifest_record.get("split", "scenario_evaluation"),
        },
        "model": {
            "name": prediction_record.get("model_name"),
            "version": prediction_record.get("model_version"),
            "parameters": parameters,
        },
        "metrics": {
            "word_error_rate": evaluation_record.get("word_error_rate"),
            "exact_match": evaluation_record.get("exact_match"),
            "denominator": 1,
        },
        "inference_elapsed_seconds": parameters.get("record_inference_elapsed_seconds"),
        "research_note": (
            "Single fixed-scenario ASR result. It does not replace the multi-record Week 2 ASR benchmark."
        ),
    }


def exactly_one_record(records: Sequence[Mapping[str, Any]], *, name: str) -> Mapping[str, Any]:
    if len(records) != 1:
        raise ValueError(f"{name} must contain exactly one record")
    return records[0]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
