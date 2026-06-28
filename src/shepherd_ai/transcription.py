"""Speech transcript generation workflow.

The roadmap calls for Whisper-based speech recognition in Week 2. This module
defines the reproducible transcript workflow and a cached-transcript baseline;
it deliberately keeps Whisper behind an optional adapter so tests and examples
do not require downloading model weights.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import importlib
from importlib import metadata
import json
from pathlib import Path
from typing import Any, Protocol

from shepherd_ai.audio_manifest import AudioManifestRecord, word_error_rate


class Transcriber(Protocol):
    """Interface for speech-to-text backends."""

    model_name: str
    model_version: str | None
    parameters: dict[str, Any]

    def transcribe(self, audio_path: Path) -> str:
        """Return transcript text for one audio file."""


@dataclass(frozen=True)
class TranscriptionResult:
    """One transcript-generation result."""

    id: str
    audio_path: Path
    expected_transcript: str
    predicted_transcript: str
    word_error_rate: float
    exact_match: bool

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["audio_path"] = str(self.audio_path)
        return payload


class CachedTranscriptTranscriber:
    """Transcriber baseline that returns manifest transcripts by audio path."""

    model_name = "cached-transcript"
    model_version = None
    parameters: dict[str, Any] = {}

    def __init__(self, transcripts_by_path: dict[Path, str]) -> None:
        self._transcripts_by_path = transcripts_by_path

    @classmethod
    def from_records(cls, records: list[AudioManifestRecord]) -> "CachedTranscriptTranscriber":
        return cls({record.audio_path: record.transcript for record in records})

    def transcribe(self, audio_path: Path) -> str:
        try:
            return self._transcripts_by_path[audio_path]
        except KeyError as exc:
            raise KeyError(f"no cached transcript for {audio_path}") from exc


class WhisperTranscriber:
    """Optional adapter for the `openai-whisper` Python package."""

    def __init__(
        self,
        *,
        model_name: str = "base",
        language: str | None = None,
        whisper_module: Any | None = None,
    ) -> None:
        self.model_name = f"whisper-{model_name}"
        self.parameters = {"model_size": model_name, "language": language}
        module = whisper_module if whisper_module is not None else _load_whisper_module()
        self.model_version = _detect_whisper_version(module)
        self._model = module.load_model(model_name)
        self._language = language

    def transcribe(self, audio_path: Path) -> str:
        options: dict[str, Any] = {}
        if self._language is not None:
            options["language"] = self._language
        result = self._model.transcribe(str(audio_path), **options)
        text = result.get("text", "")
        if not isinstance(text, str):
            raise TypeError("Whisper transcription result must contain string field 'text'")
        return text.strip()


def transcribe_records(records: list[AudioManifestRecord], transcriber: Transcriber) -> dict[str, Any]:
    """Generate transcripts for manifest records and score them."""

    rows: list[dict[str, Any]] = []
    for record in records:
        predicted = transcriber.transcribe(record.audio_path)
        wer = word_error_rate(record.transcript, predicted)
        rows.append(
            TranscriptionResult(
                id=record.id,
                audio_path=record.audio_path,
                expected_transcript=record.transcript,
                predicted_transcript=predicted,
                word_error_rate=wer,
                exact_match=wer == 0.0,
            ).to_dict()
        )

    exact_matches = sum(1 for row in rows if row["exact_match"])
    mean_wer = sum(row["word_error_rate"] for row in rows) / len(rows) if rows else 0.0
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "model_name": transcriber.model_name,
            "model_version": transcriber.model_version,
            "parameters": transcriber.parameters,
            "metric_note": "Transcript generation output; task success is not evaluated here.",
        },
        "summary": {
            "records": len(rows),
            "exact_matches": exact_matches,
            "exact_match_accuracy": exact_matches / len(rows) if rows else 0.0,
            "mean_word_error_rate": mean_wer,
        },
        "records": rows,
    }


def write_transcription_output(payload: dict[str, Any], output_path: str | Path) -> None:
    """Write raw transcript output JSON."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _load_whisper_module() -> Any:
    try:
        return importlib.import_module("whisper")
    except ImportError as exc:
        raise RuntimeError(
            "Whisper is not installed. Install the optional speech dependency before "
            "using WhisperTranscriber."
        ) from exc


def _detect_whisper_version(module: Any) -> str | None:
    module_version = getattr(module, "__version__", None)
    if isinstance(module_version, str) and module_version:
        return module_version
    try:
        return metadata.version("openai-whisper")
    except metadata.PackageNotFoundError:
        return None
