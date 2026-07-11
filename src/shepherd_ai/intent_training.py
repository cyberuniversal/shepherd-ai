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

from shepherd_ai.intent import (
    ACTION_PATTERNS,
    DETERMINISTIC_PARSER_NAME,
    LOCATION_ALIASES,
    TARGET_ALIASES,
    MissionIntent,
    parse_intent,
)


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
    feature_config: dict[str, Any] | None = None

    def predict(self, text: str) -> str | None:
        tokens = _extract_features(text, self.feature_config, field=self.field)
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
            feature_config=dict(payload.get("feature_config") or {}),
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
        use_rule_overrides = bool((self.parameters or {}).get("use_rule_overrides", False))
        predicted_action = self.field_models["action"].predict(text)
        predicted_location = self.field_models["location"].predict(text)
        predicted_target = self.field_models["target"].predict(text)
        return MissionIntent(
            action=rule_intent.action if use_rule_overrides else predicted_action,
            count=rule_intent.count,
            location=rule_intent.location if use_rule_overrides else predicted_location,
            target=rule_intent.target if use_rule_overrides else predicted_target,
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


def train_intent_model(
    records: list[LabeledCommand],
    *,
    model_name: str = "trained_nb_v0",
    model_version: str = "0.1",
    include_bigrams: bool = False,
    include_alias_features: bool = False,
    alias_feature_weight: int = 3,
    use_rule_overrides: bool = False,
) -> TrainedIntentModel:
    if not records:
        raise ValueError("at least one labeled training record is required")
    validate_split_integrity(records)
    feature_config = {
        "include_unigrams": True,
        "include_bigrams": include_bigrams,
        "include_alias_features": include_alias_features,
        "alias_feature_weight": alias_feature_weight,
    }
    return TrainedIntentModel(
        field_models={field: _train_field_model(records, field, feature_config) for field in FIELDS},
        trained_records=len(records),
        model_name=model_name,
        model_version=model_version,
        parameters={
            "classifier": "multinomial_naive_bayes",
            "alpha": 1.0,
            "feature_config": feature_config,
            "use_rule_overrides": use_rule_overrides,
        },
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
    error_analysis = analyze_intent_errors({"records": rows})
    data_types = sorted({record.data_type for record in records})
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "model_name": model.model_name,
            "model_version": model.model_version,
            "dataset": dataset_name,
            "data_types": data_types,
            "parameters": model.parameters or {"classifier": "multinomial_naive_bayes", "alpha": 1.0},
            "note": _evaluation_note(data_types),
        },
        "summary": {
            "records": len(rows),
            "exact_record_matches": exact_matches,
            "exact_record_accuracy": exact_matches / len(rows) if rows else 0.0,
            "field_matches": matched_fields,
            "total_fields": total_fields,
            "field_accuracy": matched_fields / total_fields if total_fields else 0.0,
            "field_error_counts": error_analysis["field_error_counts"],
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
        DETERMINISTIC_PARSER_NAME,
        lambda text: parse_intent(text).to_dict(),
        records,
        dataset_name=dataset_name,
    )
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "dataset": dataset_name,
            "systems_compared": [DETERMINISTIC_PARSER_NAME, model.model_name],
            "note": "Held-out comparison; interpret according to each system's data_types metadata.",
        },
        "systems": {
            DETERMINISTIC_PARSER_NAME: deterministic,
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


def summarize_labeled_commands(records: list[LabeledCommand]) -> dict[str, Any]:
    """Return split, provenance, and label counts for experiment metadata."""

    split_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    data_type_counts: Counter[str] = Counter()
    label_counts: dict[str, Counter[str]] = {field: Counter() for field in EVAL_FIELDS}
    for record in records:
        split_counts[record.split] += 1
        source_counts[record.source] += 1
        data_type_counts[record.data_type] += 1
        for field in EVAL_FIELDS:
            label_counts[field][_encode_label(record.expected_intent[field])] += 1

    return {
        "records": len(records),
        "split_counts": dict(sorted(split_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "data_type_counts": dict(sorted(data_type_counts.items())),
        "label_counts": {
            field: {_decode_label_for_summary(label): count for label, count in sorted(counts.items())}
            for field, counts in label_counts.items()
        },
    }


def analyze_intent_errors(evaluation_result: dict[str, Any]) -> dict[str, Any]:
    """Group held-out intent errors by field without changing raw records."""

    errors_by_field: dict[str, list[dict[str, Any]]] = {}
    for row in evaluation_result.get("records", []):
        matches = dict(row.get("field_matches") or {})
        for field, matched in matches.items():
            if matched:
                continue
            errors_by_field.setdefault(field, []).append(
                {
                    "id": row["id"],
                    "split": row["split"],
                    "text": row["text"],
                    "expected": row["expected_intent"][field],
                    "actual": row["actual_intent"][field],
                }
            )

    return {
        "field_error_counts": {field: len(errors) for field, errors in sorted(errors_by_field.items())},
        "errors_by_field": {field: errors for field, errors in sorted(errors_by_field.items())},
    }


def _train_field_model(
    records: list[LabeledCommand],
    field: str,
    feature_config: dict[str, Any],
) -> NaiveBayesFieldModel:
    class_doc_counts: Counter[str] = Counter()
    token_counts: dict[str, Counter[str]] = defaultdict(Counter)
    vocabulary: set[str] = set()
    for record in records:
        label = _encode_label(record.expected_intent[field])
        tokens = _extract_features(record.text, feature_config, field=field)
        class_doc_counts[label] += 1
        token_counts[label].update(tokens)
        vocabulary.update(tokens)
    return NaiveBayesFieldModel(
        field=field,
        class_doc_counts=dict(class_doc_counts),
        token_counts={label: dict(counts) for label, counts in token_counts.items()},
        vocabulary=sorted(vocabulary),
        feature_config=feature_config,
    )


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _extract_features(text: str, feature_config: dict[str, Any] | None, *, field: str) -> list[str]:
    config = {
        "include_unigrams": True,
        "include_bigrams": False,
        "include_alias_features": False,
        "alias_feature_weight": 1,
    }
    config.update(feature_config or {})
    tokens = _tokenize(text)
    features: list[str] = []
    if config["include_unigrams"]:
        features.extend(tokens)
    if config["include_bigrams"]:
        features.extend(f"bigram:{left}_{right}" for left, right in zip(tokens, tokens[1:]))
    if config["include_alias_features"]:
        alias_features = _schema_alias_features(text, field=field)
        for _ in range(int(config["alias_feature_weight"])):
            features.extend(alias_features)
    return features


def _schema_alias_features(text: str, *, field: str) -> list[str]:
    normalized = _normalize_text(text)
    features: list[str] = []
    if field == "action":
        for action, aliases in ACTION_PATTERNS:
            if any(_contains_alias(normalized, alias) for alias in aliases):
                features.append(f"schema_action:{action}")
    elif field == "location":
        for location, aliases in LOCATION_ALIASES:
            if any(_contains_alias(normalized, alias) for alias in aliases):
                features.append(f"schema_location:{location}")
    elif field == "target":
        for target, aliases in TARGET_ALIASES:
            if any(_contains_alias(normalized, alias) for alias in aliases):
                features.append(f"schema_target:{target}")
    return features


def _contains_alias(normalized_text: str, phrase: str) -> bool:
    normalized_phrase = _normalize_text(phrase)
    escaped = re.escape(normalized_phrase)
    return re.search(rf"\b{escaped}\b", normalized_text) is not None


def _normalize_text(text: str) -> str:
    return " ".join(_tokenize(text))


def _encode_label(value: Any) -> str:
    return NONE_LABEL if value is None else str(value)


def _decode_label(label: str | None) -> str | None:
    if label is None or label == NONE_LABEL:
        return None
    return label


def _decode_label_for_summary(label: str) -> str:
    return "null" if label == NONE_LABEL else label


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
    error_analysis = analyze_intent_errors({"records": rows})
    data_types = sorted({record.data_type for record in records})
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "model_name": model_name,
            "dataset": dataset_name,
            "data_types": data_types,
            "note": _evaluation_note(data_types),
        },
        "summary": {
            "records": len(rows),
            "exact_record_matches": exact_matches,
            "exact_record_accuracy": exact_matches / len(rows) if rows else 0.0,
            "field_matches": matched_fields,
            "total_fields": total_fields,
            "field_accuracy": matched_fields / total_fields if total_fields else 0.0,
            "field_error_counts": error_analysis["field_error_counts"],
        },
        "records": rows,
    }


def _evaluation_note(data_types: list[str]) -> str:
    if data_types == ["synthetic_command"]:
        return "Synthetic command evaluation; not evidence of real user or speech performance."
    if any("audio" in data_type or "asr" in data_type for data_type in data_types):
        return "Transcript-derived command evaluation; ASR quality must be evaluated separately."
    return "Text command evaluation; not evidence of speech recognition performance."
