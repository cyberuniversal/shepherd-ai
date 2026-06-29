"""Trainable intent extraction baseline for Week 2.

This module provides a small deterministic training baseline for labeled
command data. It is intentionally lightweight for local tests and Colab
notebooks, while preserving the key research contract: train on explicit
splits, evaluate on held-out records, and record model metadata.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from typing import Any

from shepherd_ai.intent import MissionIntent, parse_intent


FIELDS = ("action", "location", "target")
EVAL_FIELDS = ("action", "count", "location", "target", "constraints")
NONE_LABEL = "__none__"
REQUIRED_RECORD_FIELDS = ("id", "text", "split", "source", "data_type", "expected_intent")


@dataclass(frozen=True)
class LabeledCommand:
    id: str
    text: str
    split: str
    source: str
    data_type: str
    expected_intent: dict[str, Any]


@dataclass(frozen=True)
class NaiveBayesFieldModel:
    field: str
    class_doc_counts: dict[str, int]
    token_counts: dict[str, dict[str, int]]
    vocabulary: list[str]

    def predict(self, text: str) -> str | None:
        tokens = _tokenize(text)
        total_docs = sum(self.class_doc_counts.values())
        if total_docs == 0:
            return None
        vocab_size = max(len(self.vocabulary), 1)
        best_label: str | None = None
        best_score = -math.inf
        for label in sorted(self.class_doc_counts):
            class_docs = self.class_doc_counts[label]
            score = math.log(class_docs / total_docs)
            counts = self.token_counts[label]
            token_total = sum(counts.values())
            for token in tokens:
                score += math.log((counts.get(token, 0) + 1) / (token_total + vocab_size))
            if score > best_score:
                best_score = score
                best_label = label
        return _decode_label(best_label)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NaiveBayesFieldModel":
        return cls(
            field=payload["field"],
            class_doc_counts={str(k): int(v) for k, v in payload["class_doc_counts"].items()},
            token_counts={
                str(label): {str(token): int(count) for token, count in counts.items()}
                for label, counts in payload["token_counts"].items()
            },
            vocabulary=[str(token) for token in payload["vocabulary"]],
        )


@dataclass(frozen=True)
class TrainedIntentModel:
    field_models: dict[str, NaiveBayesFieldModel]
    trained_records: int
    model_name: str = "trained_nb_v0"
    model_version: str = "0.1"
    parameters: dict[str, Any] | None = None
    training_metadata: dict[str, Any] | None = None

    def predict(self, text: str) -> MissionIntent:
        rule_intent = parse_intent(text)
        return MissionIntent(
            action=self.field_models["action"].predict(text),
            count=rule_intent.count,
            location=self.field_models["location"].predict(text),
            target=self.field_models["target"].predict(text),
            constraints=rule_intent.constraints,
            text=text,
            parser=self.model_name,
            notes=[],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "trained_records": self.trained_records,
            "parameters": self.parameters or {"classifier": "multinomial_naive_bayes", "alpha": 1.0},
            "training_metadata": self.training_metadata or {},
            "field_models": {field: model.to_dict() for field, model in self.field_models.items()},
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TrainedIntentModel":
        return cls(
            model_name=payload["model_name"],
            model_version=payload["model_version"],
            trained_records=int(payload["trained_records"]),
            parameters=dict(payload.get("parameters") or {}),
            training_metadata=dict(payload.get("training_metadata") or {}),
            field_models={
                field: NaiveBayesFieldModel.from_dict(model_payload)
                for field, model_payload in payload["field_models"].items()
            },
        )


def load_labeled_commands(path: str | Path) -> list[LabeledCommand]:
    records: list[LabeledCommand] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        missing = [field for field in REQUIRED_RECORD_FIELDS if field not in raw]
        if missing:
            raise ValueError(f"line {line_number}: missing required fields: {', '.join(missing)}")
        expected = dict(raw["expected_intent"])
        for field in EVAL_FIELDS:
            if field not in expected:
                raise ValueError(f"line {line_number}: expected_intent missing {field}")
        records.append(
            LabeledCommand(
                id=_required_text(raw["id"], "id", line_number),
                text=_required_text(raw["text"], "text", line_number),
                split=_required_text(raw["split"], "split", line_number),
                source=_required_text(raw["source"], "source", line_number),
                data_type=_required_text(raw["data_type"], "data_type", line_number),
                expected_intent=expected,
            )
        )
    return records


def train_intent_model(records: list[LabeledCommand]) -> TrainedIntentModel:
    if not records:
        raise ValueError("at least one labeled training record is required")
    validate_split_integrity(records)
    return TrainedIntentModel(
        field_models={field: _train_field_model(records, field) for field in FIELDS},
        trained_records=len(records),
    )


def validate_split_integrity(records: list[LabeledCommand]) -> None:
    allowed_splits = {"train", "validation", "test"}
    ids: set[str] = set()
    text_to_split: dict[str, str] = {}
    for record in records:
        if record.split not in allowed_splits:
            raise ValueError(f"{record.id}: invalid split {record.split!r}")
        if record.id in ids:
            raise ValueError(f"duplicate command id: {record.id}")
        ids.add(record.id)
        normalized_text = _normalize_text(record.text)
        existing_split = text_to_split.get(normalized_text)
        if existing_split is not None and existing_split != record.split:
            raise ValueError(f"duplicate command text across splits: {record.text!r}")
        text_to_split[normalized_text] = record.split


def evaluate_intent_model(
    model: TrainedIntentModel,
    records: list[LabeledCommand],
    *,
    dataset_name: str,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total_fields = 0
    matched_fields = 0
    for record in records:
        predicted = model.predict(record.text).to_dict()
        actual = {field: predicted[field] for field in EVAL_FIELDS}
        matches = {field: record.expected_intent[field] == actual[field] for field in EVAL_FIELDS}
        total_fields += len(matches)
        matched_fields += sum(1 for ok in matches.values() if ok)
        rows.append(
            {
                "id": record.id,
                "split": record.split,
                "source": record.source,
                "data_type": record.data_type,
                "text": record.text,
                "expected_intent": record.expected_intent,
                "actual_intent": actual,
                "field_matches": matches,
                "all_fields_match": all(matches.values()),
            }
        )

    exact_matches = sum(1 for row in rows if row["all_fields_match"])
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "model_name": model.model_name,
            "model_version": model.model_version,
            "dataset": dataset_name,
            "parameters": model.parameters or {"classifier": "multinomial_naive_bayes", "alpha": 1.0},
            "note": "Synthetic command evaluation; not evidence of real user or speech performance.",
        },
        "summary": {
            "records": len(rows),
            "exact_record_matches": exact_matches,
            "exact_record_accuracy": exact_matches / len(rows) if rows else 0.0,
            "field_matches": matched_fields,
            "total_fields": total_fields,
            "field_accuracy": matched_fields / total_fields if total_fields else 0.0,
        },
        "records": rows,
    }


def compare_with_deterministic_baseline(
    model: TrainedIntentModel,
    records: list[LabeledCommand],
    *,
    dataset_name: str,
) -> dict[str, Any]:
    trained = evaluate_intent_model(model, records, dataset_name=dataset_name)
    deterministic = _evaluate_predictor(
        "deterministic_v0",
        lambda text: parse_intent(text).to_dict(),
        records,
        dataset_name=dataset_name,
    )
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "dataset": dataset_name,
            "systems_compared": ["deterministic_v0", model.model_name],
            "note": "Synthetic held-out comparison; not evidence of real user or speech performance.",
        },
        "systems": {
            "deterministic_v0": deterministic,
            model.model_name: trained,
        },
    }


def save_intent_model(model: TrainedIntentModel, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(model.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


def with_training_metadata(model: TrainedIntentModel, metadata: dict[str, Any]) -> TrainedIntentModel:
    return TrainedIntentModel(
        field_models=model.field_models,
        trained_records=model.trained_records,
        model_name=model.model_name,
        model_version=model.model_version,
        parameters=model.parameters,
        training_metadata=metadata,
    )


def load_intent_model(path: str | Path) -> TrainedIntentModel:
    return TrainedIntentModel.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def _train_field_model(records: list[LabeledCommand], field: str) -> NaiveBayesFieldModel:
    class_doc_counts: Counter[str] = Counter()
    token_counts: dict[str, Counter[str]] = defaultdict(Counter)
    vocabulary: set[str] = set()
    for record in records:
        label = _encode_label(record.expected_intent[field])
        tokens = _tokenize(record.text)
        class_doc_counts[label] += 1
        token_counts[label].update(tokens)
        vocabulary.update(tokens)
    return NaiveBayesFieldModel(
        field=field,
        class_doc_counts=dict(class_doc_counts),
        token_counts={label: dict(counts) for label, counts in token_counts.items()},
        vocabulary=sorted(vocabulary),
    )


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _normalize_text(text: str) -> str:
    return " ".join(_tokenize(text))


def _encode_label(value: Any) -> str:
    return NONE_LABEL if value is None else str(value)


def _decode_label(label: str | None) -> str | None:
    if label is None or label == NONE_LABEL:
        return None
    return label


def _required_text(value: Any, field_name: str, line_number: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"line {line_number}: {field_name} must be a non-empty string")
    return value.strip()


def _evaluate_predictor(
    model_name: str,
    predict: Any,
    records: list[LabeledCommand],
    *,
    dataset_name: str,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total_fields = 0
    matched_fields = 0
    for record in records:
        predicted = predict(record.text)
        actual = {field: predicted[field] for field in EVAL_FIELDS}
        matches = {field: record.expected_intent[field] == actual[field] for field in EVAL_FIELDS}
        total_fields += len(matches)
        matched_fields += sum(1 for ok in matches.values() if ok)
        rows.append(
            {
                "id": record.id,
                "split": record.split,
                "source": record.source,
                "data_type": record.data_type,
                "text": record.text,
                "expected_intent": record.expected_intent,
                "actual_intent": actual,
                "field_matches": matches,
                "all_fields_match": all(matches.values()),
            }
        )
    exact_matches = sum(1 for row in rows if row["all_fields_match"])
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "model_name": model_name,
            "dataset": dataset_name,
            "note": "Synthetic command evaluation; not evidence of real user or speech performance.",
        },
        "summary": {
            "records": len(rows),
            "exact_record_matches": exact_matches,
            "exact_record_accuracy": exact_matches / len(rows) if rows else 0.0,
            "field_matches": matched_fields,
            "total_fields": total_fields,
            "field_accuracy": matched_fields / total_fields if total_fields else 0.0,
        },
        "records": rows,
    }
