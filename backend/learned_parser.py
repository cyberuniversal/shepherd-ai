import argparse
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

try:
    from backend.mission_dataset import (
        DEFAULT_ADVERSARIAL_PATH,
        DEFAULT_BENCHMARK_PATH,
        EVALUATED_INTENT_FIELDS,
        load_examples,
        validate_dataset,
    )
except ImportError:
    from mission_dataset import (
        DEFAULT_ADVERSARIAL_PATH,
        DEFAULT_BENCHMARK_PATH,
        EVALUATED_INTENT_FIELDS,
        load_examples,
        validate_dataset,
    )


ARTIFACT_SCHEMA = "shepherd-learned-parser-baseline/1.0"
DEFAULT_ARTIFACT_PATH = Path(".tmp_models/learned_parser_baseline.json")
DEFAULT_REPORT_PATH = Path(".tmp_models/learned_parser_report.json")
FLEET_SIZE_LIMIT = 13
ALLOWED_ACTIONS = {
    "attack",
    "cancel",
    "hold",
    "inspect",
    "land",
    "patrol",
    "recon",
    "rendezvous",
    "return",
    "scout",
    "secure",
    "unknown",
}
ALLOWED_PATTERNS = {
    "circle",
    "corridor",
    "direct",
    "grid",
    "lawn_mower",
    "perimeter",
    "return_to_launch",
    "search",
    "spiral",
    "stationary",
}
ALLOWED_PRIORITIES = {"high", "medium", "low"}
ALLOWED_TARGET_REFERENCES = {"operator", "operator_relative", None}
BOUNDED_OUTPUT_FIELDS = {
    "action",
    "target_zone",
    "target_reference",
    "drone_count",
    "priority",
    "pattern",
    "needs_confirmation",
    "confidence",
    "clarifying_question",
    "parser",
    "model_id",
    "model_digest",
}


class StrictIntentAdapter:
    """Converts learned model predictions into bounded intent JSON only."""

    def __init__(self, artifact: Dict, min_similarity: float = 0.2):
        if artifact.get("schema") != ARTIFACT_SCHEMA:
            raise ValueError(f"Unsupported learned parser artifact schema: {artifact.get('schema')}")
        self.artifact = artifact
        self.min_similarity = min_similarity
        self.training_examples = artifact.get("training_examples", [])
        if not self.training_examples:
            raise ValueError("Learned parser artifact has no training examples")

    @classmethod
    def from_path(cls, artifact_path: str | Path, min_similarity: float = 0.2) -> "StrictIntentAdapter":
        with Path(artifact_path).open("r", encoding="utf-8") as handle:
            return cls(json.load(handle), min_similarity=min_similarity)

    def predict(self, command: str) -> Dict:
        query_features = _feature_counts(command)
        best_example, similarity = self._nearest_example(query_features)
        raw_intent = dict(best_example.get("expected_intent", {}))
        confidence = round(max(0.0, min(float(similarity), 1.0)), 3)
        if confidence < self.min_similarity:
            raw_intent = {
                "action": "scout",
                "target_zone": "unknown",
                "drone_count": 1,
                "pattern": "direct",
            }
        return coerce_bounded_intent(
            raw_intent,
            confidence=confidence,
            model_id=self.artifact.get("model_id"),
            model_digest=self.artifact.get("artifact_digest"),
        )

    def _nearest_example(self, query_features: Dict[str, int]) -> Tuple[Dict, float]:
        best_example = self.training_examples[0]
        best_score = -1.0
        for example in self.training_examples:
            score = _cosine_similarity(query_features, example.get("features", {}))
            if score > best_score:
                best_example = example
                best_score = score
        return best_example, best_score


def coerce_bounded_intent(
    raw_intent: Dict,
    *,
    confidence: float,
    model_id: str | None,
    model_digest: str | None,
) -> Dict:
    action = _coerce_string(raw_intent.get("action"), "scout")
    pattern = _coerce_string(raw_intent.get("pattern"), "direct")
    priority = _coerce_string(raw_intent.get("priority"), "medium")
    target_zone = _coerce_string(raw_intent.get("target_zone"), "unknown")
    target_reference = raw_intent.get("target_reference")
    if isinstance(target_reference, str):
        target_reference = target_reference.strip().lower() or None
    if target_reference not in ALLOWED_TARGET_REFERENCES:
        target_reference = None

    try:
        drone_count = int(raw_intent.get("drone_count", 1))
    except (TypeError, ValueError):
        drone_count = 1

    bounded = {
        "action": action if action in ALLOWED_ACTIONS else "unknown",
        "target_zone": target_zone or "unknown",
        "target_reference": target_reference,
        "drone_count": max(1, min(FLEET_SIZE_LIMIT, drone_count)),
        "priority": priority if priority in ALLOWED_PRIORITIES else "medium",
        "pattern": pattern if pattern in ALLOWED_PATTERNS else "direct",
        "needs_confirmation": True,
        "confidence": round(max(0.0, min(float(confidence), 1.0)), 3),
        "clarifying_question": raw_intent.get("clarifying_question"),
        "parser": "learned_baseline",
        "model_id": model_id,
        "model_digest": model_digest,
    }
    if bounded["target_zone"] == "unknown" and not bounded["clarifying_question"]:
        bounded["clarifying_question"] = "Which target zone should Shepherd-AI resolve for this mission?"
    return {key: bounded[key] for key in sorted(BOUNDED_OUTPUT_FIELDS)}


def train_baseline_model(
    dataset_path: str | Path = DEFAULT_BENCHMARK_PATH,
    *,
    adversarial_path: str | Path | None = DEFAULT_ADVERSARIAL_PATH,
    artifact_path: str | Path | None = DEFAULT_ARTIFACT_PATH,
    report_path: str | Path | None = DEFAULT_REPORT_PATH,
) -> Dict:
    splits = load_frozen_splits(dataset_path, adversarial_path=adversarial_path)
    training_examples = [_artifact_example(example) for example in splits["train"]]
    artifact = {
        "schema": ARTIFACT_SCHEMA,
        "model_id": "nearest-ngram-intent-baseline",
        "model_type": "nearest_ngram_intent",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract": {
            "output": "bounded_intent_json_only",
            "dispatch_authority": False,
            "confirmation_required": True,
            "deterministic_backend_required": True,
        },
        "feature_config": {
            "word_ngrams": [1, 2],
            "char_ngrams": [3, 4, 5],
        },
        "dataset": {
            "path": str(Path(dataset_path)),
            "adversarial_path": str(Path(adversarial_path)) if adversarial_path else None,
            "train_ids": [example["id"] for example in splits["train"]],
            "eval_ids": [example["id"] for example in splits["eval"]],
            "holdout_ids": [example["id"] for example in splits["holdout"]],
            "adversarial_ids": [example["id"] for example in splits["adversarial"]],
        },
        "training_examples": training_examples,
        "bounded_output_fields": sorted(BOUNDED_OUTPUT_FIELDS),
    }
    artifact["artifact_digest"] = _digest_without_field(artifact, "artifact_digest")

    report = evaluate_artifact_on_splits(artifact, splits)
    if artifact_path:
        _write_json(artifact, artifact_path)
    if report_path:
        _write_json(report, report_path)
    return {
        "artifact": artifact,
        "report": report,
        "artifact_path": str(Path(artifact_path)) if artifact_path else None,
        "report_path": str(Path(report_path)) if report_path else None,
    }


def load_frozen_splits(
    dataset_path: str | Path = DEFAULT_BENCHMARK_PATH,
    *,
    adversarial_path: str | Path | None = DEFAULT_ADVERSARIAL_PATH,
) -> Dict[str, List[Dict]]:
    validation = validate_dataset(dataset_path)
    if not validation["valid"]:
        raise ValueError(f"Dataset validation failed: {validation['errors']}")

    splits = {"train": [], "eval": [], "holdout": [], "adversarial": []}
    for example in load_examples(dataset_path):
        splits[example["split"]].append(example)

    if adversarial_path:
        adversarial_validation = validate_dataset(adversarial_path)
        if not adversarial_validation["valid"]:
            raise ValueError(f"Adversarial validation failed: {adversarial_validation['errors']}")
        for example in load_examples(adversarial_path):
            if example["split"] != "holdout":
                raise ValueError(f"{example['id']}: adversarial rows must keep split=holdout")
            splits["adversarial"].append(example)

    return splits


def evaluate_artifact_on_splits(artifact: Dict, splits: Dict[str, List[Dict]]) -> Dict:
    adapter = StrictIntentAdapter(artifact)
    split_reports = {
        split_name: evaluate_adapter(adapter, rows, split_name=split_name)
        for split_name, rows in splits.items()
    }
    return {
        "schema": "shepherd-learned-parser-report/1.0",
        "model_id": artifact.get("model_id"),
        "artifact_digest": artifact.get("artifact_digest"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract": artifact.get("contract"),
        "split_reports": split_reports,
        "summary": {
            "train_count": len(splits["train"]),
            "eval_count": len(splits["eval"]),
            "holdout_count": len(splits["holdout"]),
            "adversarial_count": len(splits["adversarial"]),
            "adversarial_used_for_training": False,
        },
    }


def evaluate_adapter(adapter: StrictIntentAdapter, examples: Iterable[Dict], *, split_name: str) -> Dict:
    rows = list(examples)
    results = []
    field_totals = {field: 0 for field in EVALUATED_INTENT_FIELDS}
    field_matches = {field: 0 for field in EVALUATED_INTENT_FIELDS}
    subset_matches = 0
    bounded_outputs = 0

    for example in rows:
        predicted = adapter.predict(example["command"])
        expected = example["expected_intent"]
        field_results = {}
        for field in EVALUATED_INTENT_FIELDS:
            if field not in expected:
                continue
            expected_value = expected.get(field)
            predicted_value = predicted.get(field)
            matched = _normalize_value(expected_value) == _normalize_value(predicted_value)
            field_totals[field] += 1
            if matched:
                field_matches[field] += 1
            field_results[field] = {
                "expected": expected_value,
                "predicted": predicted_value,
                "matched": matched,
            }

        subset_match = all(result["matched"] for result in field_results.values())
        if subset_match:
            subset_matches += 1
        if set(predicted).issubset(BOUNDED_OUTPUT_FIELDS) and predicted.get("needs_confirmation") is True:
            bounded_outputs += 1
        results.append({
            "id": example["id"],
            "language": example["language"],
            "split": split_name,
            "command": example["command"],
            "subset_match": subset_match,
            "field_results": field_results,
            "bounded_output": predicted,
        })

    field_metrics = {
        field: {
            "matched": field_matches[field],
            "total": field_totals[field],
            "accuracy": round(field_matches[field] / field_totals[field], 3) if field_totals[field] else None,
        }
        for field in EVALUATED_INTENT_FIELDS
    }
    return {
        "split": split_name,
        "total": len(rows),
        "subset_matches": subset_matches,
        "subset_accuracy": round(subset_matches / len(rows), 3) if rows else None,
        "bounded_output_count": bounded_outputs,
        "field_metrics": field_metrics,
        "results": results,
    }


def load_artifact(path: str | Path = DEFAULT_ARTIFACT_PATH) -> Dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _artifact_example(example: Dict) -> Dict:
    return {
        "id": example["id"],
        "language": example["language"],
        "command": example["command"],
        "expected_intent": example["expected_intent"],
        "expected_constraints": example["expected_constraints"],
        "should_clarify": bool(example["should_clarify"]),
        "features": _feature_counts(example["command"]),
    }


def _feature_counts(text: str) -> Dict[str, int]:
    normalized = _normalize_text(text)
    tokens = normalized.split()
    features = Counter()
    for size in (1, 2):
        for index in range(0, max(0, len(tokens) - size + 1)):
            features[f"w{size}:{' '.join(tokens[index:index + size])}"] += 1
    compact = normalized.replace(" ", "_")
    for size in (3, 4, 5):
        for index in range(0, max(0, len(compact) - size + 1)):
            features[f"c{size}:{compact[index:index + size]}"] += 1
    return dict(features)


def _normalize_text(text: str) -> str:
    lowered = text.lower()
    tokens = re.findall(r"[\w]+", lowered, flags=re.UNICODE)
    return " ".join(tokens)


def _cosine_similarity(left: Dict[str, int], right: Dict[str, int]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    if dot == 0:
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _normalize_value(value):
    if isinstance(value, str):
        return " ".join(value.lower().strip().split())
    return value


def _coerce_string(value, default: str) -> str:
    if value is None:
        return default
    return str(value).strip().lower() or default


def _digest_without_field(payload: Dict, field: str) -> str:
    clone = dict(payload)
    clone.pop(field, None)
    encoded = json.dumps(clone, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _write_json(payload: Dict, path: str | Path) -> str:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return str(output_path)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Train or evaluate Shepherd-AI learned parser baselines.")
    subparsers = parser.add_subparsers(dest="command")

    train_parser = subparsers.add_parser("train-baseline", help="Train the nearest-ngram intent baseline.")
    train_parser.add_argument("--dataset", default=str(DEFAULT_BENCHMARK_PATH), help="Benchmark JSONL dataset path.")
    train_parser.add_argument("--adversarial", default=str(DEFAULT_ADVERSARIAL_PATH), help="Adversarial holdout JSONL path.")
    train_parser.add_argument("--output", default=str(DEFAULT_ARTIFACT_PATH), help="Output artifact path.")
    train_parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="Output JSON report path.")

    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate a learned parser artifact.")
    evaluate_parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT_PATH), help="Learned parser artifact path.")
    evaluate_parser.add_argument("--dataset", default=str(DEFAULT_BENCHMARK_PATH), help="Benchmark JSONL dataset path.")
    evaluate_parser.add_argument("--adversarial", default=str(DEFAULT_ADVERSARIAL_PATH), help="Adversarial holdout JSONL path.")
    evaluate_parser.add_argument("--report", default=None, help="Optional output JSON report path.")
    evaluate_parser.add_argument("--summary-only", action="store_true", help="Omit per-row evaluation results.")

    predict_parser = subparsers.add_parser("predict", help="Run bounded intent prediction from an artifact.")
    predict_parser.add_argument("command_text", help="Operator command to parse.")
    predict_parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT_PATH), help="Learned parser artifact path.")

    args = parser.parse_args()
    command = args.command or "train-baseline"

    if command == "train-baseline":
        result = train_baseline_model(
            args.dataset,
            adversarial_path=args.adversarial,
            artifact_path=args.output,
            report_path=args.report,
        )
        print(json.dumps(_without_training_examples(result), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if command == "evaluate":
        artifact = load_artifact(args.artifact)
        splits = load_frozen_splits(args.dataset, adversarial_path=args.adversarial)
        report = evaluate_artifact_on_splits(artifact, splits)
        if args.report:
            report["report_path"] = _write_json(report, args.report)
        if args.summary_only:
            report = _summary_only(report)
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if command == "predict":
        adapter = StrictIntentAdapter.from_path(args.artifact)
        print(json.dumps(adapter.predict(args.command_text), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    parser.print_help()
    return 1


def _without_training_examples(result: Dict) -> Dict:
    clone = json.loads(json.dumps(result))
    clone["artifact"]["training_examples"] = f"{len(result['artifact'].get('training_examples', []))} rows omitted"
    dataset = clone.get("artifact", {}).get("dataset", {})
    for key in ("train_ids", "eval_ids", "holdout_ids", "adversarial_ids"):
        if key in dataset:
            dataset[key] = f"{len(result['artifact']['dataset'].get(key, []))} ids omitted"
    for split_report in clone.get("report", {}).get("split_reports", {}).values():
        split_report.pop("results", None)
    return clone


def _summary_only(report: Dict) -> Dict:
    clone = json.loads(json.dumps(report))
    for split_report in clone.get("split_reports", {}).values():
        split_report.pop("results", None)
    return clone


if __name__ == "__main__":
    raise SystemExit(main())
