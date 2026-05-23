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
        DEFAULT_AUGMENTATION_PATH,
        DEFAULT_ADVERSARIAL_PATH,
        DEFAULT_BENCHMARK_PATH,
        EVALUATED_INTENT_FIELDS,
        load_examples,
        validate_dataset,
    )
    from backend.targeting import apply_target_metadata
except ImportError:
    from mission_dataset import (
        DEFAULT_AUGMENTATION_PATH,
        DEFAULT_ADVERSARIAL_PATH,
        DEFAULT_BENCHMARK_PATH,
        EVALUATED_INTENT_FIELDS,
        load_examples,
        validate_dataset,
    )
    from targeting import apply_target_metadata


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
    "target",
    "target_zone",
    "target_raw_text",
    "target_type",
    "target_resolution_required",
    "target_metadata_schema",
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
KNOWN_TARGET_ALIASES = [
    ("king saud university", "king saud university"),
    ("ministry of defense", "ministry of defense"),
    ("riyadh boulevard", "boulevard"),
    ("national museum", "national museum"),
    ("wadi hanifah", "wadi hanifah"),
    ("masmak fort", "masmak"),
    ("al faisaliyah", "al faisaliyah"),
    ("the airport", "the airport"),
    ("al nada", "al nada"),
    ("boulevard", "boulevard"),
    ("stadium", "stadium"),
    ("diriyah", "diriyah"),
    ("masmak", "masmak"),
    ("airport", "the airport"),
    ("kafd", "kafd"),
    ("كافد", "kafd"),
    ("المركز المالي", "المركز المالي"),
    ("وزارة الدفاع", "وزارة الدفاع"),
    ("المتحف الوطني", "المتحف الوطني"),
    ("وادي حنيفة", "وادي حنيفة"),
    ("حي الندى", "حي الندى"),
    ("للندى", "حي الندى"),
    ("الندى", "حي الندى"),
    ("الدرعية", "الدرعية"),
    ("المطار", "المطار"),
    ("الملعب", "الملعب"),
    ("جامعة الامام", "جامعة الامام"),
    ("جامعة الإمام", "جامعة الامام"),
    ("المصمك", "masmak"),
    ("قصر المصمك", "masmak"),
]
AMBIGUOUS_TARGET_TERMS = [
    "anything suspicious",
    "pin i just dropped",
    "gps pin",
    "smoke plume",
    "red zone",
    "below the bridge",
    "under the bridge",
    "last place",
    "same point",
    "yesterday",
    "north gate",
    "compound",
    "the target",
    "that place",
    "that area",
    "the area",
    "somewhere",
    "أي شيء",
    "دبوس الخريطة",
    "عمود الدخان",
    "المنطقة الحمراء",
    "تحت الجسر",
    "آخر مكان",
    "نفس نقطة",
    "نقطة أمس",
    "أمس",
    "البوابة الشمالية",
    "المجمع",
    "الهدف",
    "للهدف",
    "للمنطقة",
    "ذلك المكان",
    "تلك المنطقة",
    "المنطقة",
]
OPERATOR_TARGET_TERMS = [
    "my current location",
    "my location",
    "my position",
    "near me",
    "to me",
    "around here",
    "here",
    "موقعي الحالي",
    "موقعي",
    "عندي",
    "قريب مني",
    "حولي",
    "لي أنا",
]
OPERATOR_RELATIVE_TERMS = [
    "east of my position",
    "west of my position",
    "north of my position",
    "south of my position",
    "meters from me",
    "meters east",
    "meters west",
    "meters north",
    "meters south",
    "متر شرق موقعي",
    "متر غرب موقعي",
    "متر شمال موقعي",
    "متر جنوب موقعي",
]
HOME_TARGET_TERMS = ["return to launch", "back to base", "to base", "base", "home", "rtb", "القاعدة", "المنزل"]
CURRENT_POSITION_TERMS = ["current position", "current positions", "مواقعها الحالية", "موقعه الحالي"]
ROUTE_BETWEEN_TERMS = ["between", "from", "corridor", "الممر بين", "المسار بين", "بين"]
KNOWN_DRONE_IDS = [
    "alpha-1",
    "alpha-2",
    "alpha-3",
    "alpha-4",
    "alpha-5",
    "beta-1",
    "beta-2",
    "beta-3",
    "gamma-1",
    "gamma-2",
    "gamma-3",
    "delta-1",
    "delta-2",
]
COUNT_WORDS = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "pair": 2,
    "couple": 2,
    "several": 3,
    "واحد": 1,
    "واحدة": 1,
    "طائرة": 1,
    "درون": 1,
    "درونين": 2,
    "طائرتين": 2,
    "طائرتان": 2,
    "اثنين": 2,
    "إثنين": 2,
    "اثنتين": 2,
    "إثنتين": 2,
    "اثنان": 2,
    "ثلاثة": 3,
    "ثلاث": 3,
    "أربعة": 4,
    "اربعة": 4,
    "أربع": 4,
    "اربع": 4,
    "خمس": 5,
    "خمسة": 5,
}
UNKNOWN_ACTION_TERMS = [
    "stay away from",
    "but stay away",
    "recall them immediately",
    "return them immediately",
    "ثم رجعهم فور",
    "لكن ابتعد",
]
ACTION_TERM_RULES = [
    ("cancel", ["do not send", "don't send", "do not launch", "don't launch", "cancel", "abort", "لا ترسل", "لا تشغل", "ألغ", "الغ"]),
    ("hold", ["hold", "hold position", "on station", "stay on station", "stationary", "ثبت", "ثبّت", "خله ثابت", "خل درون واحد ثابت"]),
    ("land", ["land", "هبط", "اهبط"]),
    ("patrol", ["patrol", "دورية"]),
    ("inspect", ["inspect", "فتش"]),
    ("secure", ["secure", "protect", "defend", "أمن", "امّن", "تأمين", "حماية"]),
    ("recon", ["recon", "reconnaissance", "observe", "راقب", "مراقبة"]),
    ("rendezvous", ["bring backup", "bring", "come to", "rendezvous", "meet", "link up", "جيب", "أحضر"]),
    ("return", ["return to launch", "return", "recall", "come back", "rtb", "back to base", "ارجع", "رجع", "أعد", "اعادة"]),
    ("scout", ["scout", "scan", "search", "sweep", "cover", "check", "send", "deploy", "dispatch", "move", "take", "go to", "route", "launch", "استطلع", "امسح", "افحص", "أرسل", "ارسل", "وجه", "حرك", "خذ", "شغل"]),
]
PATTERN_TERM_RULES = [
    ("spiral", ["spiral", "حلزوني"]),
    ("circle", ["circle", "orbit", "يدور", "دائري"]),
    ("corridor", ["corridor", "between", "from", "الممر بين", "المسار بين", "بين"]),
    ("grid", ["grid", "square", "cover that area", "north of us", "around my location in a square", "شبكي", "مربع", "غط المنطقة", "شمالنا"]),
    ("search", ["find anything", "anything suspicious", "if nothing", "أي شيء مريب", "إذا ما ظهر"]),
    ("lawn_mower", ["search", "scan", "sweep", "مسح", "بحث"]),
    ("perimeter", ["perimeter", "secure", "surround", "محيط", "تأمين"]),
    ("direct", ["direct", "directly", "straight", "by the direct route", "مباشرة", "الطريق المباشر"]),
]
HIGH_PRIORITY_TERMS = ["urgent", "critical", "emergency", "fast", "عاجل", "بسرعة", "طوارئ", "حرج"]
LOW_PRIORITY_TERMS = ["low priority", "when possible", "غير عاجل"]


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
        raw_intent = _apply_deterministic_intent_slots(command, raw_intent)
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
    parser_name: str = "learned_baseline",
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
        "parser": parser_name,
        "model_id": model_id,
        "model_digest": model_digest,
    }
    for target_field in ("target", "target_raw_text", "target_type", "target_resolution_required", "target_metadata_schema"):
        if target_field in raw_intent:
            bounded[target_field] = raw_intent[target_field]
    bounded = apply_target_metadata(bounded)
    if bounded["target_zone"] == "unknown" and not bounded["clarifying_question"]:
        bounded["clarifying_question"] = "Which target zone should Shepherd-AI resolve for this mission?"
    return {key: bounded[key] for key in sorted(BOUNDED_OUTPUT_FIELDS)}


def apply_deterministic_intent_slots(command: str, raw_intent: Dict) -> Dict:
    """Apply command-text slot guards without creating dispatch authority."""
    return _apply_deterministic_intent_slots(command, raw_intent)


def train_baseline_model(
    dataset_path: str | Path = DEFAULT_BENCHMARK_PATH,
    *,
    augmentation_path: str | Path | None = None,
    adversarial_path: str | Path | None = DEFAULT_ADVERSARIAL_PATH,
    artifact_path: str | Path | None = DEFAULT_ARTIFACT_PATH,
    report_path: str | Path | None = DEFAULT_REPORT_PATH,
) -> Dict:
    splits = load_frozen_splits(dataset_path, augmentation_path=augmentation_path, adversarial_path=adversarial_path)
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
            "augmentation_path": str(Path(augmentation_path)) if augmentation_path else None,
            "adversarial_path": str(Path(adversarial_path)) if adversarial_path else None,
            "train_ids": [example["id"] for example in splits["train"]],
            "augmentation_ids": [example["id"] for example in splits.get("augmentation", [])],
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
    augmentation_path: str | Path | None = None,
    adversarial_path: str | Path | None = DEFAULT_ADVERSARIAL_PATH,
) -> Dict[str, List[Dict]]:
    validation = validate_dataset(dataset_path)
    if not validation["valid"]:
        raise ValueError(f"Dataset validation failed: {validation['errors']}")

    splits = {"train": [], "eval": [], "holdout": [], "adversarial": [], "augmentation": []}
    for example in load_examples(dataset_path):
        splits[example["split"]].append(example)

    if augmentation_path:
        augmentation_validation = validate_dataset(augmentation_path)
        if not augmentation_validation["valid"]:
            raise ValueError(f"Augmentation validation failed: {augmentation_validation['errors']}")
        for example in load_examples(augmentation_path):
            if example["split"] != "train":
                raise ValueError(f"{example['id']}: augmentation rows must keep split=train")
            splits["augmentation"].append(example)
            splits["train"].append(example)

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
            "augmentation_count": len(splits.get("augmentation", [])),
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
        expected = apply_target_metadata(example["expected_intent"])
        field_results = {}
        for field in EVALUATED_INTENT_FIELDS:
            expected_value = _intent_field_value(expected, field)
            if expected_value is None:
                continue
            predicted_value = _intent_field_value(predicted, field)
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


def _intent_field_value(intent: Dict, field: str):
    if "." not in field:
        return intent.get(field)
    value = intent
    for part in field.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _apply_deterministic_intent_slots(command: str, raw_intent: Dict) -> Dict:
    normalized_command = _normalize_command_for_matching(command)
    intent = dict(raw_intent)
    target_zone, target_reference = _resolve_target_slots(normalized_command)
    if target_zone:
        intent["target_zone"] = target_zone
    if target_reference is not None or target_zone == "operator_current_position":
        intent["target_reference"] = target_reference
    if target_zone == "unknown":
        intent["target_reference"] = None
    action = _resolve_action_slot(normalized_command, intent)
    if action:
        intent["action"] = action
    drone_count = _resolve_drone_count_slot(normalized_command, intent.get("action"))
    if drone_count is not None:
        intent["drone_count"] = drone_count
    pattern = _resolve_pattern_slot(normalized_command, intent)
    if pattern:
        intent["pattern"] = pattern
    priority = _resolve_priority_slot(normalized_command, intent)
    if priority:
        intent["priority"] = priority
    return intent


def _resolve_target_slots(normalized_command: str) -> Tuple[str | None, str | None]:
    if _has_coordinates(normalized_command):
        return "coordinates", None

    if _contains_any(normalized_command, CURRENT_POSITION_TERMS):
        return "current_position", None

    if _contains_any(normalized_command, HOME_TARGET_TERMS):
        return "home", None

    known_targets = _known_targets_in_command(normalized_command)
    distinct_targets = []
    for target in known_targets:
        if target not in distinct_targets:
            distinct_targets.append(target)

    if len(distinct_targets) >= 2:
        if _contains_any(normalized_command, ROUTE_BETWEEN_TERMS):
            return "route_between_known_zones", None
        if " then " not in normalized_command and " ثم " not in normalized_command:
            return "multi_target", None
        return distinct_targets[0], None

    if distinct_targets:
        return distinct_targets[0], None

    if _contains_any(normalized_command, AMBIGUOUS_TARGET_TERMS):
        return "unknown", None

    if _contains_any(normalized_command, OPERATOR_RELATIVE_TERMS):
        return "operator_current_position", "operator_relative"

    if _contains_any(normalized_command, OPERATOR_TARGET_TERMS):
        return "operator_current_position", "operator"

    return None, None


def _resolve_action_slot(normalized_command: str, intent: Dict) -> str | None:
    if _contains_any(normalized_command, UNKNOWN_ACTION_TERMS):
        return "unknown"
    if _contains_any(normalized_command, OPERATOR_TARGET_TERMS) and _contains_any(
        normalized_command,
        ["bring", "come to", "return", "رجع", "جيب"],
    ):
        return "rendezvous"
    for action, terms in ACTION_TERM_RULES:
        if _contains_any(normalized_command, terms):
            if action == "return" and intent.get("target_reference") in {"operator", "operator_relative"}:
                return "rendezvous"
            if action == "land" and _contains_any(normalized_command, ["same point", "نفس نقطة", "أمس"]):
                return "scout"
            return action
    return None


def _resolve_pattern_slot(normalized_command: str, intent: Dict) -> str | None:
    action = intent.get("action")
    target_zone = intent.get("target_zone")
    if action == "return":
        return "return_to_launch"
    if action == "hold":
        return "stationary"
    if action in {"land", "cancel", "rendezvous"}:
        return "direct"
    for pattern, terms in PATTERN_TERM_RULES:
        if _contains_any(normalized_command, terms):
            return pattern
    if target_zone in {"unknown", "coordinates", "operator_current_position", "multi_target", "route_between_known_zones"}:
        return "direct"
    if action in {"secure", "recon", "scout"} and target_zone:
        return "perimeter"
    return None


def _resolve_priority_slot(normalized_command: str, intent: Dict) -> str | None:
    if _contains_any(normalized_command, LOW_PRIORITY_TERMS):
        return "low"
    if intent.get("action") in {"return", "cancel", "land"}:
        return "high"
    if _contains_any(normalized_command, HIGH_PRIORITY_TERMS):
        return "high"
    return "medium"


def _resolve_drone_count_slot(normalized_command: str, action: str | None) -> int | None:
    explicit_drones = {drone_id for drone_id in KNOWN_DRONE_IDS if _contains_phrase(normalized_command, drone_id)}
    if explicit_drones:
        return len(explicit_drones)
    if action == "return" and _contains_any(normalized_command, ["all", "every", "كل", "الكل", "جميع"]):
        return FLEET_SIZE_LIMIT

    if _contains_any(normalized_command, ["pair", "couple", "درونين", "طائرتين", "طائرتان"]):
        return 2

    multi_target_count = _sum_multi_target_counts(normalized_command)
    if multi_target_count is not None:
        return multi_target_count

    direct_count = _first_count_before_vehicle(normalized_command)
    if direct_count is not None:
        return direct_count

    if _contains_any(normalized_command, ["backup"]):
        return 1
    return None


def _sum_multi_target_counts(normalized_command: str) -> int | None:
    if not _contains_any(normalized_command, [" and ", " و"]):
        return None
    counts = []
    for match in re.finditer(
        r"(?<![-\w])(\d+|one|two|three|four|five|six|seven|eight|nine|ten|واحد|واحدة|اثنين|إثنين|اثنتين|إثنتين|ثلاثة|ثلاث|أربعة|اربعة|أربع|اربع|خمس|خمسة)\s+(?:drone|drones|to|درون|درونات|طائرة|طائرات|ل|لل|إلى|الى)",
        normalized_command,
        flags=re.IGNORECASE | re.UNICODE,
    ):
        value = _count_token_value(match.group(1))
        if value is not None:
            counts.append(value)
    if len(counts) >= 2:
        return max(1, min(FLEET_SIZE_LIMIT, sum(counts)))
    return None


def _first_count_before_vehicle(normalized_command: str) -> int | None:
    patterns = [
        r"(?<![-\w])(\d+|one|two|three|four|five|six|seven|eight|nine|ten|a|an|several)\s+(?:drone|drones|unit|units)",
        r"(?:with|using)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|a|an|several)\s+(?:drone|drones|unit|units)",
        r"(?:send|deploy|dispatch|move|take|route|guide|bring|launch)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|a|an|several)\b",
        r"(?<![-\w])(\d+|واحد|واحدة|اثنين|إثنين|اثنتين|إثنتين|ثلاثة|ثلاث|أربعة|اربعة|أربع|اربع|خمس|خمسة)\s+(?:درون|درونات|طائرة|طائرات)",
        r"(?:أرسل|ارسل|وجه|حرك|خذ|شغل|افحص|فتش|ثبت|رجع|أعد)\s+(\d+|واحد|واحدة|اثنين|إثنين|اثنتين|إثنتين|ثلاثة|ثلاث|أربعة|اربعة|أربع|اربع|خمس|خمسة)\b",
        r"(?:ب|بـ)\s*(\d+|واحد|واحدة|اثنين|إثنين|اثنتين|إثنتين|ثلاثة|ثلاث|أربعة|اربعة|أربع|اربع|خمس|خمسة)\s+(?:درون|درونات|طائرة|طائرات)",
        r"(?:درون|درونات|طائرة|طائرات)\s+(\d+|واحد|واحدة|اثنين|إثنين|اثنتين|إثنتين|ثلاثة|ثلاث|أربعة|اربعة|أربع|اربع|خمس|خمسة)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_command, flags=re.IGNORECASE | re.UNICODE)
        if match:
            value = _count_token_value(match.group(1))
            if value is not None:
                return max(1, min(FLEET_SIZE_LIMIT, value))
    return None


def _count_token_value(token: str) -> int | None:
    normalized = token.strip().lower()
    if normalized.isdigit():
        return int(normalized)
    return COUNT_WORDS.get(normalized)


def _known_targets_in_command(normalized_command: str) -> List[str]:
    matches = []
    for alias, canonical in sorted(KNOWN_TARGET_ALIASES, key=lambda item: len(item[0]), reverse=True):
        normalized_alias = _normalize_command_for_matching(alias)
        if _contains_phrase(normalized_command, normalized_alias):
            matches.append(canonical)
    return matches


def _contains_any(normalized_command: str, terms: List[str]) -> bool:
    return any(_contains_phrase(normalized_command, _normalize_command_for_matching(term)) for term in terms)


def _contains_phrase(normalized_command: str, normalized_phrase: str) -> bool:
    if not normalized_phrase:
        return False
    if re.search(r"[A-Za-z0-9_]", normalized_phrase):
        return re.search(rf"(?<!\w){re.escape(normalized_phrase)}(?!\w)", normalized_command) is not None
    return normalized_phrase in normalized_command


def _normalize_command_for_matching(text: str) -> str:
    normalized = text.lower()
    normalized = normalized.replace("?", " ").replace("!", " ")
    normalized = normalized.replace("ـ", "")
    normalized = re.sub(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]", "", normalized, flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized, flags=re.UNICODE)
    return normalized.strip()


def _has_coordinates(normalized_command: str) -> bool:
    decimal_pair = re.search(r"\b-?\d{1,2}\s*\.\s*\d+\s*(?:,|and|\s)\s*-?\d{1,3}\s*\.\s*\d+\b", normalized_command)
    if decimal_pair:
        return True
    spoken_decimal_pair = re.search(
        r"\b\d{1,2}\s+(?:point|فاصلة)\s+\d+\s+(?:and|و)\s+\d{1,3}\s+(?:point|فاصلة)\s+\d+\b",
        normalized_command,
    )
    return spoken_decimal_pair is not None


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
    train_parser.add_argument("--augmentation", default=None, help="Optional train-only augmentation JSONL path.")
    train_parser.add_argument("--adversarial", default=str(DEFAULT_ADVERSARIAL_PATH), help="Adversarial holdout JSONL path.")
    train_parser.add_argument("--output", default=str(DEFAULT_ARTIFACT_PATH), help="Output artifact path.")
    train_parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="Output JSON report path.")

    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate a learned parser artifact.")
    evaluate_parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT_PATH), help="Learned parser artifact path.")
    evaluate_parser.add_argument("--dataset", default=str(DEFAULT_BENCHMARK_PATH), help="Benchmark JSONL dataset path.")
    evaluate_parser.add_argument("--augmentation", default=None, help="Optional train-only augmentation JSONL path.")
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
            augmentation_path=args.augmentation,
            adversarial_path=args.adversarial,
            artifact_path=args.output,
            report_path=args.report,
        )
        print(json.dumps(_without_training_examples(result), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if command == "evaluate":
        artifact = load_artifact(args.artifact)
        splits = load_frozen_splits(args.dataset, augmentation_path=args.augmentation, adversarial_path=args.adversarial)
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
    for key in ("train_ids", "augmentation_ids", "eval_ids", "holdout_ids", "adversarial_ids"):
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
