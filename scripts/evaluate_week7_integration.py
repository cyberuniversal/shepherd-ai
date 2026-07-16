"""Evaluate bounded integration of the implemented Week 2-7 module interfaces."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations  # noqa: E402
from shepherd_ai.integrated_prototype import run_integrated_prototype  # noqa: E402
from shepherd_ai.intent_training import load_intent_model  # noqa: E402
from shepherd_ai.safety import load_safety_policy  # noqa: E402
from shepherd_ai.whisper_asr import load_whisper_predictions  # noqa: E402


DEFAULT_CASES = ROOT / "datasets" / "safety" / "week7_integration_cases_v1.jsonl"
DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_FLEET = ROOT / "datasets" / "drones" / "week5_three_drone_fleet_v1.json"
DEFAULT_POLICY = ROOT / "datasets" / "safety" / "week7_safety_policy_v1.json"
DEFAULT_INTENT_MODEL = ROOT / "outputs" / "model_artifacts" / "intent_nb_human_curated_v2.json"
DEFAULT_WHISPER = ROOT / "outputs" / "evaluations" / "whisper_base_audio_predictions_local_gtx1650.jsonl"
DEFAULT_VISION = ROOT / "outputs" / "evaluations" / "week6_visdrone_yolov8n_seed17_e50_completed_summary.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "evaluations" / "week7_integration_development_v1.json"
DEFAULT_REPORT = ROOT / "reports" / "week7_integration_development_v1.md"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--fleet", type=Path, default=DEFAULT_FLEET)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--intent-model", type=Path, default=DEFAULT_INTENT_MODEL)
    parser.add_argument("--whisper-predictions", type=Path, default=DEFAULT_WHISPER)
    parser.add_argument("--vision-artifact", type=Path, default=DEFAULT_VISION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    cases = _read_jsonl(args.cases)
    locations = load_map_locations(args.map)
    fleet = _read_json(args.fleet)
    policy = load_safety_policy(args.policy)
    intent_model = load_intent_model(args.intent_model)
    predictions = {
        str(row["id"]): row for row in load_whisper_predictions(args.whisper_predictions)
    }
    vision_payload = _read_json(args.vision_artifact)
    vision = {
        "artifact_path": str(args.vision_artifact.relative_to(ROOT)),
        "payload": vision_payload,
        "scope": "week6_development_result_not_mission_specific",
    }
    rows: list[dict[str, Any]] = []
    integrated_stages: set[str] = set()
    for case in cases:
        input_payload = dict(case["input"])
        if input_payload.get("input_type") == "whisper_prediction":
            prediction_id = str(input_payload.pop("prediction_id"))
            if prediction_id not in predictions:
                raise ValueError(f"unknown registered Whisper prediction: {prediction_id}")
            input_payload["prediction"] = predictions[prediction_id]
        result = run_integrated_prototype(
            input_payload,
            intent_system=str(case["intent_system"]),
            locations=locations,
            fleet_payload=fleet,
            safety_policy=policy,
            trained_intent_model=intent_model,
            vision_artifact=vision,
        )
        case_stages = [str(stage["stage"]) for stage in result["stages"]]
        integrated_stages.update(case_stages)
        rows.append(
            {
                "case_id": str(case["case_id"]),
                "data_type": "synthetic_or_stored_artifact_week7_integration_case",
                "case_input": case,
                "expected_status": str(case["expected_status"]),
                "actual_status": result["status"],
                "status_matches_expected": result["status"] == case["expected_status"],
                "stages": case_stages,
                "prototype_result": result,
                "notes": list(case.get("notes", [])),
            }
        )

    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "evaluator": "bounded_week7_prior_module_integration_evaluator_v1",
            "python_version": platform.python_version(),
            "random_seed": None,
            "data_scope": "synthetic_commands_plus_stored_asr_and_vision_artifacts",
            "integrated_stages": sorted(integrated_stages),
            "input_sha256": {
                "cases": _sha256(args.cases),
                "map": _sha256(args.map),
                "fleet": _sha256(args.fleet),
                "policy": _sha256(args.policy),
                "intent_model": _sha256(args.intent_model),
                "whisper_predictions": _sha256(args.whisper_predictions),
                "vision_artifact": _sha256(args.vision_artifact),
            },
            "research_note": (
                "This evaluates module contracts. ASR and vision models are not rerun, and the Week 6 "
                "vision result is not treated as mission-specific imagery or end-to-end success."
            ),
        },
        "summary": {
            "case_count": len(rows),
            "expected_status_matches": sum(row["status_matches_expected"] for row in rows),
        },
        "cases": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text(_render_report(payload), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    print(f"Wrote {args.output}")
    print(f"Wrote {args.report_output}")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON input must contain an object: {path}")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError("integration cases must contain at least one JSON object")
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Week 7 Prior-Module Integration Evaluation",
        "",
        "This evaluates bounded software interfaces, not a Week 8 end-to-end mission result.",
        "",
        f"- Cases: `{summary['case_count']}`",
        f"- Expected status matches: `{summary['expected_status_matches']}`",
        f"- Integrated stages: `{', '.join(payload['metadata']['integrated_stages'])}`",
        "",
        "| Case | Input | Intent system | Expected | Actual |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in payload["cases"]:
        case = row["case_input"]
        lines.append(
            f"| {row['case_id']} | {case['input']['input_type']} | {case['intent_system']} | "
            f"{row['expected_status']} | {row['actual_status']} |"
        )
    lines.extend(
        [
            "",
            "The stored Week 6 artifact is bound as development evidence only. It is not an image captured by these simulated missions.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
