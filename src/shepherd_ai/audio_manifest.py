"""Audio manifest and transcript-evaluation utilities.

This is Milestone 2 scaffolding. It validates explicit audio/transcript
metadata and evaluates transcript text, but it does not run Whisper inference.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any
from collections import Counter


REQUIRED_FIELDS = ("id", "audio_path", "transcript", "source", "data_type", "split")


class AudioManifestError(ValueError):
    """Raised when an audio manifest is malformed or unsafe to load."""


@dataclass(frozen=True)
class AudioManifestRecord:
    """One labeled audio command entry."""

    id: str
    audio_path: Path
    transcript: str
    source: str
    data_type: str
    split: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["audio_path"] = str(self.audio_path)
        return payload


def load_audio_manifest(path: str | Path, *, dataset_root: str | Path) -> list[AudioManifestRecord]:
    """Load and validate a JSONL audio manifest.

    Each non-empty line must contain `id`, `audio_path`, `transcript`, `source`,
    `data_type`, and `split`. Audio paths are resolved relative to
    `dataset_root` and must stay within it.
    """

    manifest_path = Path(path)
    root = Path(dataset_root).resolve()
    records: list[AudioManifestRecord] = []

    for line_number, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AudioManifestError(f"line {line_number}: invalid JSON") from exc

        missing = [field for field in REQUIRED_FIELDS if field not in raw]
        if missing:
            raise AudioManifestError(f"line {line_number}: missing required fields: {', '.join(missing)}")

        audio_path = _resolve_audio_path(root, raw["audio_path"], line_number)
        if audio_path.suffix.lower() != ".wav":
            raise AudioManifestError(f"line {line_number}: audio_path must point to a WAV file")
        if not audio_path.exists():
            raise AudioManifestError(f"line {line_number}: audio file does not exist: {audio_path}")

        records.append(
            AudioManifestRecord(
                id=_required_text(raw["id"], "id", line_number),
                audio_path=audio_path,
                transcript=_required_text(raw["transcript"], "transcript", line_number),
                source=_required_text(raw["source"], "source", line_number),
                data_type=_required_text(raw["data_type"], "data_type", line_number),
                split=_required_text(raw["split"], "split", line_number),
            )
        )

    return records


def word_error_rate(reference: str, hypothesis: str) -> float:
    """Compute word error rate using Levenshtein edit distance."""

    reference_words = _words(reference)
    hypothesis_words = _words(hypothesis)
    if not reference_words:
        return 0.0 if not hypothesis_words else 1.0
    return _edit_distance(reference_words, hypothesis_words) / len(reference_words)


def evaluate_transcripts(
    expected: dict[str, str],
    predicted: dict[str, str],
    *,
    model_name: str,
    model_version: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare expected and predicted transcripts by record id."""

    rows: list[dict[str, Any]] = []
    for record_id in sorted(expected):
        reference = expected[record_id]
        hypothesis = predicted.get(record_id, "")
        rows.append(
            {
                "id": record_id,
                "expected": reference,
                "predicted": hypothesis,
                "word_error_rate": word_error_rate(reference, hypothesis),
                "exact_match": _normalize_text(reference) == _normalize_text(hypothesis),
            }
        )

    exact_matches = sum(1 for row in rows if row["exact_match"])
    mean_wer = sum(row["word_error_rate"] for row in rows) / len(rows) if rows else 0.0
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "model_name": model_name,
            "model_version": model_version,
            "parameters": parameters or {},
            "metric_note": "Transcript text evaluation only; no speech model inference is run here.",
        },
        "summary": {
            "records": len(rows),
            "exact_matches": exact_matches,
            "exact_match_accuracy": exact_matches / len(rows) if rows else 0.0,
            "mean_word_error_rate": mean_wer,
        },
        "records": rows,
    }


def summarize_audio_manifest(records: list[AudioManifestRecord]) -> dict[str, Any]:
    """Return split, provenance, and data-type counts for audio records."""

    split_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    data_type_counts: Counter[str] = Counter()
    for record in records:
        split_counts[record.split] += 1
        source_counts[record.source] += 1
        data_type_counts[record.data_type] += 1

    return {
        "records": len(records),
        "split_counts": dict(sorted(split_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "data_type_counts": dict(sorted(data_type_counts.items())),
    }


def _resolve_audio_path(root: Path, raw_path: str, line_number: int) -> Path:
    candidate = (root / raw_path).resolve()
    if not candidate.is_relative_to(root):
        raise AudioManifestError(f"line {line_number}: audio_path must stay within dataset_root")
    return candidate


def _required_text(value: Any, field_name: str, line_number: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AudioManifestError(f"line {line_number}: {field_name} must be a non-empty string")
    return value.strip()


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _normalize_text(text: str) -> str:
    return " ".join(_words(text))


def _edit_distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for i, ref_word in enumerate(reference, start=1):
        current = [i]
        for j, hyp_word in enumerate(hypothesis, start=1):
            cost = 0 if ref_word == hyp_word else 1
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + cost,
                )
            )
        previous = current
    return previous[-1]
