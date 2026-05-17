import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

try:
    from backend.learned_parser import (
        DEFAULT_ARTIFACT_PATH,
        evaluate_artifact_on_splits,
        load_artifact,
        load_frozen_splits,
    )
    from backend.mission_dataset import DEFAULT_ADVERSARIAL_PATH, DEFAULT_BENCHMARK_PATH
except ImportError:
    from learned_parser import DEFAULT_ARTIFACT_PATH, evaluate_artifact_on_splits, load_artifact, load_frozen_splits
    from mission_dataset import DEFAULT_ADVERSARIAL_PATH, DEFAULT_BENCHMARK_PATH


PROMOTION_SCHEMA = "shepherd-parser-promotion-gate/1.0"
DEFAULT_PROMOTION_REPORT_PATH = Path(".tmp_models/parser_promotion_gate.json")
DEFAULT_THRESHOLDS = {
    "eval": {
        "subset_accuracy": 0.80,
        "bounded_output_rate": 1.0,
        "field_metrics": {
            "action": 0.95,
            "drone_count": 0.90,
            "pattern": 0.90,
            "target_zone": 0.90,
        },
    },
    "holdout": {
        "subset_accuracy": 0.70,
        "bounded_output_rate": 1.0,
        "field_metrics": {
            "action": 0.90,
            "drone_count": 0.85,
            "pattern": 0.85,
            "target_zone": 0.85,
        },
    },
    "adversarial": {
        "subset_accuracy": 0.35,
        "bounded_output_rate": 1.0,
        "field_metrics": {
            "action": 0.75,
            "drone_count": 0.70,
            "pattern": 0.60,
            "target_zone": 0.60,
        },
    },
}


def run_promotion_gate(
    artifact_path: str | Path = DEFAULT_ARTIFACT_PATH,
    *,
    dataset_path: str | Path = DEFAULT_BENCHMARK_PATH,
    adversarial_path: str | Path | None = DEFAULT_ADVERSARIAL_PATH,
    thresholds: Dict | None = None,
    report_path: str | Path | None = DEFAULT_PROMOTION_REPORT_PATH,
) -> Dict:
    artifact = load_artifact(artifact_path)
    splits = load_frozen_splits(dataset_path, adversarial_path=adversarial_path)
    evaluation = evaluate_artifact_on_splits(artifact, splits)
    active_thresholds = thresholds or DEFAULT_THRESHOLDS
    contract_checks = _contract_checks(artifact, evaluation)
    split_checks = {
        split_name: _check_split(evaluation["split_reports"][split_name], active_thresholds[split_name])
        for split_name in ("eval", "holdout", "adversarial")
    }
    failures = _flatten_failures(contract_checks, split_checks)
    report = {
        "schema": PROMOTION_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "artifact_path": str(Path(artifact_path)),
        "model_id": artifact.get("model_id"),
        "artifact_digest": artifact.get("artifact_digest"),
        "promoted": not failures,
        "thresholds": active_thresholds,
        "contract_checks": contract_checks,
        "split_checks": split_checks,
        "failures": failures,
        "summary": {
            "eval_subset_accuracy": evaluation["split_reports"]["eval"]["subset_accuracy"],
            "holdout_subset_accuracy": evaluation["split_reports"]["holdout"]["subset_accuracy"],
            "adversarial_subset_accuracy": evaluation["split_reports"]["adversarial"]["subset_accuracy"],
            "adversarial_used_for_training": evaluation["summary"].get("adversarial_used_for_training"),
        },
    }
    if report_path:
        _write_json(report, report_path)
        report["report_path"] = str(Path(report_path))
    return report


def _contract_checks(artifact: Dict, evaluation: Dict) -> Dict:
    contract = artifact.get("contract", {})
    dataset = artifact.get("dataset", {})
    train_ids = set(dataset.get("train_ids", []))
    adversarial_ids = set(dataset.get("adversarial_ids", []))
    split_reports = evaluation.get("split_reports", {})
    bounded_failures = []
    for split_name in ("eval", "holdout", "adversarial"):
        split_report = split_reports.get(split_name, {})
        total = split_report.get("total", 0)
        bounded_count = split_report.get("bounded_output_count", 0)
        if bounded_count != total:
            bounded_failures.append(f"{split_name}: {bounded_count}/{total} bounded outputs")

    checks = {
        "bounded_intent_json_only": contract.get("output") == "bounded_intent_json_only",
        "dispatch_authority_false": contract.get("dispatch_authority") is False,
        "confirmation_required": contract.get("confirmation_required") is True,
        "deterministic_backend_required": contract.get("deterministic_backend_required") is True,
        "artifact_digest_present": bool(artifact.get("artifact_digest")),
        "adversarial_not_used_for_training": evaluation["summary"].get("adversarial_used_for_training") is False,
        "train_adversarial_disjoint": train_ids.isdisjoint(adversarial_ids),
        "all_outputs_bounded": not bounded_failures,
        "bounded_failures": bounded_failures,
    }
    checks["passed"] = all(
        value is True
        for key, value in checks.items()
        if key not in {"bounded_failures", "passed"}
    )
    return checks


def _check_split(split_report: Dict, thresholds: Dict) -> Dict:
    total = split_report.get("total", 0)
    bounded_count = split_report.get("bounded_output_count", 0)
    bounded_output_rate = bounded_count / total if total else 0.0
    failures = []
    subset_accuracy = split_report.get("subset_accuracy") or 0.0
    if subset_accuracy < thresholds["subset_accuracy"]:
        failures.append(
            _failure(
                "subset_accuracy",
                subset_accuracy,
                thresholds["subset_accuracy"],
            )
        )
    if bounded_output_rate < thresholds["bounded_output_rate"]:
        failures.append(
            _failure(
                "bounded_output_rate",
                round(bounded_output_rate, 3),
                thresholds["bounded_output_rate"],
            )
        )

    field_results = {}
    for field, minimum in thresholds.get("field_metrics", {}).items():
        metric = split_report.get("field_metrics", {}).get(field, {})
        accuracy = metric.get("accuracy")
        if accuracy is None:
            accuracy = 0.0
        passed = accuracy >= minimum
        field_results[field] = {
            "accuracy": accuracy,
            "minimum": minimum,
            "passed": passed,
        }
        if not passed:
            failures.append(_failure(f"field:{field}", accuracy, minimum))

    return {
        "split": split_report.get("split"),
        "total": total,
        "subset_accuracy": subset_accuracy,
        "bounded_output_rate": round(bounded_output_rate, 3),
        "field_results": field_results,
        "failures": failures,
        "passed": not failures,
    }


def _failure(metric: str, actual, minimum) -> Dict:
    return {
        "metric": metric,
        "actual": actual,
        "minimum": minimum,
    }


def _flatten_failures(contract_checks: Dict, split_checks: Dict[str, Dict]) -> List[Dict]:
    failures = []
    if not contract_checks.get("passed"):
        for key, value in contract_checks.items():
            if key in {"bounded_failures", "passed"}:
                continue
            if value is not True:
                failures.append({"scope": "contract", "check": key, "actual": value})
        for bounded_failure in contract_checks.get("bounded_failures", []):
            failures.append({"scope": "contract", "check": "bounded_output", "actual": bounded_failure})

    for split_name, split_check in split_checks.items():
        for failure in split_check.get("failures", []):
            failures.append({"scope": split_name, **failure})
    return failures


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

    parser = argparse.ArgumentParser(description="Gate Shepherd-AI parser artifacts before model promotion.")
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT_PATH), help="Learned parser artifact path.")
    parser.add_argument("--dataset", default=str(DEFAULT_BENCHMARK_PATH), help="Benchmark JSONL dataset path.")
    parser.add_argument("--adversarial", default=str(DEFAULT_ADVERSARIAL_PATH), help="Adversarial holdout JSONL path.")
    parser.add_argument("--report", default=str(DEFAULT_PROMOTION_REPORT_PATH), help="Output promotion report path.")
    parser.add_argument(
        "--allow-failure",
        action="store_true",
        help="Return exit code 0 even when the artifact is not promoted.",
    )
    args = parser.parse_args()

    report = run_promotion_gate(
        args.artifact,
        dataset_path=args.dataset,
        adversarial_path=args.adversarial,
        report_path=args.report,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report["promoted"] or args.allow_failure:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
