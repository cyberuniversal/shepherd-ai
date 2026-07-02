"""Trainable BIO span tagger baseline for Week 2.

This is a lightweight supervised baseline for human-verified span labels. It
does not replace later spaCy or Hugging Face experiments; it gives the project
a reproducible token-tagging baseline with held-out metrics.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any

from shepherd_ai.span_annotations import SpanLabeledCommand, load_span_labeled_commands, spans_to_bio_tags


@dataclass(frozen=True)
class SpanTagRecord:
    id: str
    text: str
    split: str
    source: str
    data_type: str
    tokens: list[str]
    offsets: list[list[int]]
    tags: list[str]


@dataclass(frozen=True)
class NaiveBayesSpanTagger:
    tag_counts: dict[str, int]
    feature_counts: dict[str, dict[str, int]]
    vocabulary: list[str]
    transition_counts: dict[str, dict[str, int]] | None = None
    model_name: str = "span_nb_v0"
    model_version: str = "0.1"
    trained_records: int = 0
    trained_tokens: int = 0
    parameters: dict[str, Any] | None = None
    training_metadata: dict[str, Any] | None = None

    def predict(self, tokens: list[str]) -> list[str]:
        if (self.parameters or {}).get("use_transitions") and self.transition_counts:
            return self._predict_viterbi(tokens)
        return [self._predict_one(tokens, index) for index in range(len(tokens))]

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "trained_records": self.trained_records,
            "trained_tokens": self.trained_tokens,
            "tag_counts": self.tag_counts,
            "feature_counts": self.feature_counts,
            "vocabulary": self.vocabulary,
            "transition_counts": self.transition_counts or {},
            "parameters": self.parameters or {"classifier": "multinomial_naive_bayes", "alpha": 1.0},
            "training_metadata": self.training_metadata or {},
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NaiveBayesSpanTagger":
        return cls(
            model_name=payload["model_name"],
            model_version=payload["model_version"],
            trained_records=int(payload["trained_records"]),
            trained_tokens=int(payload["trained_tokens"]),
            tag_counts={str(tag): int(count) for tag, count in payload["tag_counts"].items()},
            feature_counts={
                str(tag): {str(feature): int(count) for feature, count in counts.items()}
                for tag, counts in payload["feature_counts"].items()
            },
            vocabulary=[str(feature) for feature in payload["vocabulary"]],
            transition_counts={
                str(previous): {str(tag): int(count) for tag, count in counts.items()}
                for previous, counts in dict(payload.get("transition_counts") or {}).items()
            },
            parameters=dict(payload.get("parameters") or {}),
            training_metadata=dict(payload.get("training_metadata") or {}),
        )

    def _predict_one(self, tokens: list[str], index: int) -> str:
        scores = self._tag_log_scores(tokens, index)
        return max(scores, key=scores.get) if scores else "O"

    def _tag_log_scores(self, tokens: list[str], index: int) -> dict[str, float]:
        total_tags = sum(self.tag_counts.values())
        vocab_size = max(len(self.vocabulary), 1)
        features = _token_features(tokens, index)
        scores: dict[str, float] = {}
        for tag in sorted(self.tag_counts):
            tag_total = self.tag_counts[tag]
            score = math.log(tag_total / total_tags)
            counts = self.feature_counts[tag]
            feature_total = sum(counts.values())
            for feature in features:
                score += math.log((counts.get(feature, 0) + 1) / (feature_total + vocab_size))
            scores[tag] = score
        return scores

    def _predict_viterbi(self, tokens: list[str]) -> list[str]:
        tags = sorted(self.tag_counts)
        if not tokens:
            return []
        scores_by_position: list[dict[str, float]] = []
        backpointers: list[dict[str, str]] = []
        first_scores = self._tag_log_scores(tokens, 0)
        scores_by_position.append(
            {tag: first_scores[tag] + self._transition_log_score("<START>", tag, len(tags)) for tag in tags}
        )
        backpointers.append({tag: "<START>" for tag in tags})
        for index in range(1, len(tokens)):
            emissions = self._tag_log_scores(tokens, index)
            current_scores: dict[str, float] = {}
            current_backpointers: dict[str, str] = {}
            for tag in tags:
                best_previous = tags[0]
                best_score = -math.inf
                for previous in tags:
                    score = (
                        scores_by_position[index - 1][previous]
                        + self._transition_log_score(previous, tag, len(tags))
                        + emissions[tag]
                    )
                    if score > best_score:
                        best_score = score
                        best_previous = previous
                current_scores[tag] = best_score
                current_backpointers[tag] = best_previous
            scores_by_position.append(current_scores)
            backpointers.append(current_backpointers)
        best_final = max(scores_by_position[-1], key=scores_by_position[-1].get)
        prediction = [best_final]
        for index in range(len(tokens) - 1, 0, -1):
            prediction.append(backpointers[index][prediction[-1]])
        prediction.reverse()
        return prediction

    def _transition_log_score(self, previous: str, tag: str, tag_count: int) -> float:
        counts = (self.transition_counts or {}).get(previous, {})
        total = sum(counts.values())
        return math.log((counts.get(tag, 0) + 1) / (total + tag_count))


def records_from_span_commands(path: str | Path) -> list[SpanTagRecord]:
    commands = load_span_labeled_commands(path)
    return [_record_from_command(command) for command in commands]


def train_span_tagger(
    records: list[SpanTagRecord],
    *,
    model_name: str = "span_nb_v0",
    model_version: str = "0.1",
    use_transitions: bool = False,
) -> NaiveBayesSpanTagger:
    if not records:
        raise ValueError("at least one training record is required")
    tag_counts: Counter[str] = Counter()
    feature_counts: dict[str, Counter[str]] = defaultdict(Counter)
    transition_counts: dict[str, Counter[str]] = defaultdict(Counter)
    vocabulary: set[str] = set()
    for record in records:
        if len(record.tokens) != len(record.tags):
            raise ValueError(f"{record.id}: token/tag length mismatch")
        previous = "<START>"
        for index, tag in enumerate(record.tags):
            features = _token_features(record.tokens, index)
            tag_counts[tag] += 1
            feature_counts[tag].update(features)
            transition_counts[previous][tag] += 1
            vocabulary.update(features)
            previous = tag
    return NaiveBayesSpanTagger(
        tag_counts=dict(tag_counts),
        feature_counts={tag: dict(counts) for tag, counts in feature_counts.items()},
        vocabulary=sorted(vocabulary),
        transition_counts={tag: dict(counts) for tag, counts in transition_counts.items()},
        model_name=model_name,
        model_version=model_version,
        trained_records=len(records),
        trained_tokens=sum(len(record.tokens) for record in records),
        parameters={
            "classifier": "multinomial_naive_bayes",
            "alpha": 1.0,
            "use_transitions": use_transitions,
            "features": ["token", "shape", "prefix", "suffix", "previous_token", "next_token", "position"],
        },
    )


def evaluate_span_tagger(
    model: NaiveBayesSpanTagger,
    records: list[SpanTagRecord],
    *,
    dataset_name: str,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total_tokens = 0
    matched_tokens = 0
    expected_entities_total = 0
    predicted_entities_total = 0
    matched_entities_total = 0
    for record in records:
        predicted_tags = model.predict(record.tokens)
        token_matches = [expected == actual for expected, actual in zip(record.tags, predicted_tags)]
        expected_entities = set(_entities_from_bio(record.tags, record.offsets))
        predicted_entities = set(_entities_from_bio(predicted_tags, record.offsets))
        matched_entities = expected_entities & predicted_entities
        total_tokens += len(record.tags)
        matched_tokens += sum(1 for matched in token_matches if matched)
        expected_entities_total += len(expected_entities)
        predicted_entities_total += len(predicted_entities)
        matched_entities_total += len(matched_entities)
        rows.append(
            {
                "id": record.id,
                "split": record.split,
                "text": record.text,
                "tokens": record.tokens,
                "offsets": record.offsets,
                "expected_tags": record.tags,
                "predicted_tags": predicted_tags,
                "token_matches": token_matches,
                "expected_entities": [list(entity) for entity in sorted(expected_entities)],
                "predicted_entities": [list(entity) for entity in sorted(predicted_entities)],
            }
        )
    precision = matched_entities_total / predicted_entities_total if predicted_entities_total else 0.0
    recall = matched_entities_total / expected_entities_total if expected_entities_total else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    data_types = sorted({record.data_type for record in records})
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "model_name": model.model_name,
            "model_version": model.model_version,
            "dataset": dataset_name,
            "data_types": data_types,
            "parameters": model.parameters or {"classifier": "multinomial_naive_bayes", "alpha": 1.0},
            "note": "Human-verified span command evaluation; not ASR or end-to-end mission performance.",
        },
        "summary": {
            "records": len(rows),
            "tokens": total_tokens,
            "token_matches": matched_tokens,
            "token_accuracy": matched_tokens / total_tokens if total_tokens else 0.0,
            "expected_entities": expected_entities_total,
            "predicted_entities": predicted_entities_total,
            "matched_entities": matched_entities_total,
            "entity_precision": precision,
            "entity_recall": recall,
            "entity_f1": f1,
        },
        "records": rows,
    }


def summarize_span_tag_records(records: list[SpanTagRecord]) -> dict[str, Any]:
    split_counts: Counter[str] = Counter()
    data_type_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    for record in records:
        split_counts[record.split] += 1
        data_type_counts[record.data_type] += 1
        tag_counts.update(record.tags)
    return {
        "records": len(records),
        "tokens": sum(len(record.tokens) for record in records),
        "split_counts": dict(sorted(split_counts.items())),
        "data_type_counts": dict(sorted(data_type_counts.items())),
        "tag_counts": dict(sorted(tag_counts.items())),
    }


def analyze_span_tagger_errors(evaluation_result: dict[str, Any]) -> dict[str, Any]:
    """Group BIO tagging errors by token confusion, entity field, and record."""

    token_confusion: dict[str, Counter[str]] = defaultdict(Counter)
    false_positive_entity_counts: Counter[str] = Counter()
    false_negative_entity_counts: Counter[str] = Counter()
    worst_records: list[dict[str, Any]] = []
    for row in evaluation_result.get("records", []):
        expected_tags = list(row.get("expected_tags", []))
        predicted_tags = list(row.get("predicted_tags", []))
        tokens = list(row.get("tokens", []))
        token_errors: list[dict[str, Any]] = []
        for index, (expected, predicted) in enumerate(zip(expected_tags, predicted_tags)):
            if expected == predicted:
                continue
            token_confusion[expected][predicted] += 1
            token_errors.append(
                {
                    "index": index,
                    "token": tokens[index] if index < len(tokens) else None,
                    "expected": expected,
                    "predicted": predicted,
                }
            )

        expected_entities = {_tuple_entity(entity) for entity in row.get("expected_entities", [])}
        predicted_entities = {_tuple_entity(entity) for entity in row.get("predicted_entities", [])}
        false_negatives = sorted(expected_entities - predicted_entities)
        false_positives = sorted(predicted_entities - expected_entities)
        for field, _, _ in false_negatives:
            false_negative_entity_counts[field] += 1
        for field, _, _ in false_positives:
            false_positive_entity_counts[field] += 1
        if token_errors or false_negatives or false_positives:
            token_count = max(len(expected_tags), 1)
            worst_records.append(
                {
                    "id": row.get("id"),
                    "text": row.get("text"),
                    "token_error_count": len(token_errors),
                    "token_error_rate": len(token_errors) / token_count,
                    "token_errors": token_errors,
                    "false_negative_entities": [list(entity) for entity in false_negatives],
                    "false_positive_entities": [list(entity) for entity in false_positives],
                }
            )

    worst_records.sort(key=lambda row: (-row["token_error_rate"], -row["token_error_count"], str(row["id"])))
    return {
        "token_confusion": {
            expected: dict(sorted(predicted_counts.items()))
            for expected, predicted_counts in sorted(token_confusion.items())
        },
        "false_positive_entity_counts": dict(sorted(false_positive_entity_counts.items())),
        "false_negative_entity_counts": dict(sorted(false_negative_entity_counts.items())),
        "worst_records": worst_records,
    }


def with_training_metadata(model: NaiveBayesSpanTagger, metadata: dict[str, Any]) -> NaiveBayesSpanTagger:
    return NaiveBayesSpanTagger(
        tag_counts=model.tag_counts,
        feature_counts=model.feature_counts,
        vocabulary=model.vocabulary,
        transition_counts=model.transition_counts,
        model_name=model.model_name,
        model_version=model.model_version,
        trained_records=model.trained_records,
        trained_tokens=model.trained_tokens,
        parameters=model.parameters,
        training_metadata=metadata,
    )


def save_span_tagger(model: NaiveBayesSpanTagger, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(model.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


def load_span_tagger(path: str | Path) -> NaiveBayesSpanTagger:
    return NaiveBayesSpanTagger.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def _record_from_command(command: SpanLabeledCommand) -> SpanTagRecord:
    tagged = spans_to_bio_tags(command.text, command.spans)
    return SpanTagRecord(
        id=command.id,
        text=command.text,
        split=command.split,
        source=command.source,
        data_type=command.data_type,
        tokens=[token.text for token, _ in tagged],
        offsets=[[token.start, token.end] for token, _ in tagged],
        tags=[tag for _, tag in tagged],
    )


def _token_features(tokens: list[str], index: int) -> list[str]:
    token = tokens[index]
    lower = token.lower()
    features = [
        "bias",
        f"token:{lower}",
        f"shape:{_shape(token)}",
        f"prefix1:{lower[:1]}",
        f"prefix2:{lower[:2]}",
        f"suffix1:{lower[-1:]}",
        f"suffix2:{lower[-2:]}",
        f"is_digit:{token.isdigit()}",
        f"position:{_position_bucket(index, len(tokens))}",
    ]
    if index == 0:
        features.append("BOS")
    else:
        features.append(f"prev:{tokens[index - 1].lower()}")
    if index == len(tokens) - 1:
        features.append("EOS")
    else:
        features.append(f"next:{tokens[index + 1].lower()}")
    return features


def _shape(token: str) -> str:
    chars: list[str] = []
    for char in token:
        if char.isupper():
            chars.append("X")
        elif char.islower():
            chars.append("x")
        elif char.isdigit():
            chars.append("d")
        else:
            chars.append(char)
    return "".join(chars)


def _position_bucket(index: int, length: int) -> str:
    if index == 0:
        return "first"
    if index == length - 1:
        return "last"
    return "middle"


def _entities_from_bio(tags: list[str], offsets: list[list[int]]) -> list[tuple[str, int, int]]:
    entities: list[tuple[str, int, int]] = []
    active_field: str | None = None
    active_start: int | None = None
    active_end: int | None = None
    for tag, offset in zip(tags, offsets):
        if tag == "O":
            if active_field is not None and active_start is not None and active_end is not None:
                entities.append((active_field, active_start, active_end))
            active_field = None
            active_start = None
            active_end = None
            continue
        prefix, field = tag.split("-", 1)
        if prefix == "B" or active_field != field:
            if active_field is not None and active_start is not None and active_end is not None:
                entities.append((active_field, active_start, active_end))
            active_field = field
            active_start = offset[0]
            active_end = offset[1]
        else:
            active_end = offset[1]
    if active_field is not None and active_start is not None and active_end is not None:
        entities.append((active_field, active_start, active_end))
    return entities


def _tuple_entity(entity: Any) -> tuple[str, int, int]:
    field, start, end = entity
    return str(field), int(start), int(end)
