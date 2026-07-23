"""Score raw monolithic LLM decisions against separated gold labels."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.evidence_evaluation import score_decision_rows  # noqa: E402
from shepherd_ai.monolithic_decision import (  # noqa: E402
    PROMPT_VERSION,
    validate_input_record,
)


DEFAULT_INPUTS = ROOT / "outputs" / "evaluations" / "week9_monolithic_diagnostic_inputs_v1.jsonl"
DEFAULT_GOLD = ROOT / "datasets" / "evidence" / "week9_monolithic_diagnostic_gold_v1.jsonl"
DEFAULT_RAW = ROOT / "outputs" / "evaluations" / "week9_monolithic_qwen25_7b_raw_v1.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "evaluations" / "week9_monolithic_qwen25_7b_evaluation_v1.json"
DEFAULT_REPORT = ROOT / "reports" / "week9_monolithic_qwen25_7b_evaluation_v1.md"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--raw-predictions", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    inputs = _read_jsonl(args.inputs)
    gold = _read_jsonl(args.gold)
    raw = _read_json(args.raw_predictions)
    _validate_run(inputs, gold, raw, args.inputs)
    input_index = {str(row["case_id"]): row for row in inputs}
    gold_index = {str(row["case_id"]): row for row in gold}
    predictions_by_repetition: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in raw["records"]:
        case_id = str(row["case_id"])
        repetition = int(row["repetition"])
        if case_id in predictions_by_repetition[repetition]:
            raise ValueError(
                f"duplicate prediction for case {case_id!r}, repetition {repetition}"
            )
        if row.get("prompt_sha256") != input_index[case_id]["prompt_sha256"]:
            raise ValueError(f"{case_id}: prediction prompt hash mismatch")
        predictions_by_repetition[repetition][case_id] = row

    expected_ids = set(input_index)
    repetition_results: list[dict[str, Any]] = []
    per_case_predictions: dict[str, list[str]] = defaultdict(list)
    for repetition in sorted(predictions_by_repetition):
        predictions = predictions_by_repetition[repetition]
        if set(predictions) != expected_ids:
            missing = sorted(expected_ids - set(predictions))
            extra = sorted(set(predictions) - expected_ids)
            raise ValueError(
                f"repetition {repetition} case mismatch; missing={missing}, extra={extra}"
            )
        rows = []
        latencies = []
        for case_id in sorted(expected_ids):
            raw_row = predictions[case_id]
            parsed = raw_row.get("parsed_response", {})
            decision = (
                str(parsed["decision"])
                if parsed.get("valid") is True
                else "invalid"
            )
            per_case_predictions[case_id].append(decision)
            latencies.append(float(raw_row["generation_elapsed_seconds"]))
            rows.append(
                {
                    "expected_decision": str(
                        gold_index[case_id]["expected_decision"]
                    ),
                    "predicted_decision": decision,
                }
            )
        repetition_results.append(
            {
                "repetition": repetition,
                "seed": _single_seed(predictions.values()),
                "metrics": score_decision_rows(
                    rows,
                    allow_invalid_prediction=True,
                ),
                "latency": _latency_summary(latencies),
            }
        )

    aggregate_rows = []
    case_rows = []
    for case_id in sorted(expected_ids):
        decisions = per_case_predictions[case_id]
        aggregate = _majority_decision(decisions)
        aggregate_rows.append(
            {
                "expected_decision": str(gold_index[case_id]["expected_decision"]),
                "predicted_decision": aggregate,
            }
        )
        case_rows.append(
            {
                "case_id": case_id,
                "stratum": str(gold_index[case_id]["stratum"]),
                "data_type": str(gold_index[case_id]["data_type"]),
                "expected_decision": str(gold_index[case_id]["expected_decision"]),
                "shepherd_decision": str(gold_index[case_id]["shepherd_decision"]),
                "monolithic_decisions": decisions,
                "monolithic_majority_decision": aggregate,
                "monolithic_matches_expected": (
                    aggregate == gold_index[case_id]["expected_decision"]
                ),
            }
        )
    shepherd_metrics = score_decision_rows(
        [
            {
                "expected_decision": str(row["expected_decision"]),
                "predicted_decision": str(row["shepherd_decision"]),
            }
            for row in gold
        ]
    )
    monolithic_metrics = score_decision_rows(
        aggregate_rows,
        allow_invalid_prediction=True,
    )
    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "evaluator": "week9_monolithic_decision_evaluator_v1",
            "python_version": platform.python_version(),
            "prompt_version": PROMPT_VERSION,
            "model": raw["metadata"]["model"],
            "model_revision": raw["metadata"]["model_revision"],
            "model_license": raw["metadata"].get("model_license", "not stated"),
            "generation_parameters": raw["metadata"]["generation_parameters"],
            "device": raw["metadata"]["device"],
            "package_versions": raw["metadata"]["package_versions"],
            "inputs": {
                "path": _repo_path(args.inputs),
                "sha256": _sha256(args.inputs),
            },
            "gold": {
                "path": _repo_path(args.gold),
                "sha256": _sha256(args.gold),
            },
            "raw_predictions": {
                "path": _repo_path(args.raw_predictions),
                "sha256": _sha256(args.raw_predictions),
            },
            "research_role": "diagnostic_not_fresh_human_heldout",
        },
        "summary": {
            "case_count": len(inputs),
            "repetition_count": len(repetition_results),
            "shepherd_evidence_aware_v1": shepherd_metrics,
            "monolithic_llm_majority": monolithic_metrics,
        },
        "repetitions": repetition_results,
        "cases": case_rows,
        "claim_limits": {
            "tacos_reimplementation": False,
            "fresh_human_heldout": False,
            "physical_flight": False,
            "real_world_reliability": False,
            "invalid_outputs_manually_repaired": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text(_render_report(payload), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    print(f"Wrote {args.output}")
    print(f"Wrote {args.report_output}")


def _validate_run(
    inputs: list[dict[str, Any]],
    gold: list[dict[str, Any]],
    raw: dict[str, Any],
    input_path: Path,
) -> None:
    for row in inputs:
        validate_input_record(row)
    input_ids = [str(row["case_id"]) for row in inputs]
    gold_ids = [str(row["case_id"]) for row in gold]
    if len(input_ids) != len(set(input_ids)) or len(gold_ids) != len(set(gold_ids)):
        raise ValueError("input and gold case IDs must be unique")
    if set(input_ids) != set(gold_ids):
        raise ValueError("input and gold case IDs do not match")
    metadata = raw.get("metadata", {})
    if metadata.get("status") != "completed":
        raise ValueError("raw prediction run is not completed")
    if metadata.get("gold_labels_loaded") is not False:
        raise ValueError("raw prediction metadata does not prove gold isolation")
    if metadata.get("prompt_version") != PROMPT_VERSION:
        raise ValueError("raw prediction prompt version mismatch")
    if metadata.get("input_sha256") != _sha256(input_path):
        raise ValueError("raw prediction input hash mismatch")
    raw_ids = {str(row.get("case_id")) for row in raw.get("records", [])}
    if not raw_ids <= set(input_ids):
        raise ValueError("raw predictions contain unknown case IDs")


def _majority_decision(decisions: list[str]) -> str:
    counts = Counter(decisions)
    highest = max(counts.values())
    winners = sorted(decision for decision, count in counts.items() if count == highest)
    return winners[0] if len(winners) == 1 else "invalid"


def _single_seed(rows: Any) -> int:
    seeds = {int(row["seed"]) for row in rows}
    if len(seeds) != 1:
        raise ValueError(f"one repetition contains multiple seeds: {sorted(seeds)}")
    return next(iter(seeds))


def _latency_summary(values: list[float]) -> dict[str, float]:
    return {
        "total_seconds": sum(values),
        "mean_seconds": statistics.fmean(values),
        "median_seconds": statistics.median(values),
        "minimum_seconds": min(values),
        "maximum_seconds": max(values),
    }


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON input must contain an object: {path}")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"JSONL input must contain objects: {path}")
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return str(resolved)


def _render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    shepherd = summary["shepherd_evidence_aware_v1"]
    monolithic = summary["monolithic_llm_majority"]
    lines = [
        "# Monolithic LLM Decision Baseline",
        "",
        f"- Model: `{payload['metadata']['model']}`",
        f"- Revision: `{payload['metadata']['model_revision']}`",
        f"- Device: `{payload['metadata']['device']}`",
        f"- Cases: `{summary['case_count']}`",
        f"- Repetitions: `{summary['repetition_count']}`",
        "",
        "| System | Accuracy | False refusal | Silent-proceed proxy | Clarification recall | Block recall | Invalid output |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        _metric_row("Shepherd evidence-aware", shepherd),
        _metric_row("Monolithic LLM majority", monolithic),
        "",
        "This is a diagnostic comparison on reused development evidence, not the "
        "fresh human-held-out experiment required for a final paper claim.",
        "",
        "Malformed model responses count as invalid errors and are not repaired.",
    ]
    return "\n".join(lines) + "\n"


def _metric_row(name: str, metrics: dict[str, Any]) -> str:
    return (
        f"| {name} | {_fmt(metrics['decision_accuracy'])} | "
        f"{_fmt(metrics['false_refusal_rate'])} | "
        f"{_fmt(metrics['silent_misexecution_rate'])} | "
        f"{_fmt(metrics['clarification_recall'])} | "
        f"{_fmt(metrics['block_recall'])} | "
        f"{_fmt(metrics['invalid_prediction_rate'])} |"
    )


def _fmt(value: float | None) -> str:
    return "not evaluated" if value is None else f"{value:.4f}"


if __name__ == "__main__":
    main()
