"""Evidence derivation for the fixed Week 8 roadmap scenario."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any, Mapping


EVALUATED_INTENT_FIELDS = ("action", "count", "location", "target", "constraints")
ROADMAP_CLAUSE_GOLD: dict[str, dict[str, Any]] = {
    "week8_clause_001": {
        "text": "Send two drones north to inspect crops.",
        "intent": {
            "action": "inspect",
            "count": 2,
            "location": "north",
            "target": "crops",
            "constraints": [],
        },
    },
    "week8_clause_002": {
        "text": "Send one drone east to inspect irrigation.",
        "intent": {
            "action": "inspect",
            "count": 1,
            "location": "east",
            "target": "irrigation",
            "constraints": [],
        },
    },
}
EXPECTED_GROUNDING = {
    "clause_001": "loc_north_field",
    "clause_002": "loc_east_field",
}


def evaluate_roadmap_intent_predictions(
    prediction_payload: Mapping[str, Any],
    *,
    model_path: str | Path,
    prediction_field: str = "hybrid_span_parser",
) -> dict[str, Any]:
    """Score frozen-checkpoint predictions against the roadmap specification.

    This is scenario-development evidence, not a replacement for the held-out
    Week 2 benchmark. The roadmap itself supplies the expected clause semantics.
    """

    checkpoint = Path(model_path)
    if not checkpoint.is_file():
        raise FileNotFoundError(f"model checkpoint does not exist: {checkpoint}")
    predictions = {
        str(record.get("id")): record for record in prediction_payload.get("records", [])
    }
    missing = sorted(set(ROADMAP_CLAUSE_GOLD) - set(predictions))
    if missing:
        raise ValueError(f"missing fixed roadmap predictions: {', '.join(missing)}")

    rows: list[dict[str, Any]] = []
    for clause_id, gold in ROADMAP_CLAUSE_GOLD.items():
        source = predictions[clause_id]
        actual = _project_intent(source.get(prediction_field, {}))
        expected = _project_intent(gold["intent"])
        field_matches = {
            field: actual[field] == expected[field] for field in EVALUATED_INTENT_FIELDS
        }
        rows.append(
            {
                "id": clause_id.replace("week8_", ""),
                "prediction_record_id": clause_id,
                "text": gold["text"],
                "gold_source": "roadmap_specification",
                "expected_intent": expected,
                "predicted_intent": actual,
                "field_matches": field_matches,
                "exact_match": all(field_matches.values()),
            }
        )

    exact_matches = sum(row["exact_match"] for row in rows)
    field_matches = sum(
        matched for row in rows for matched in row["field_matches"].values()
    )
    field_denominator = len(rows) * len(EVALUATED_INTENT_FIELDS)
    metadata = dict(prediction_payload.get("metadata", {}))
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scenario_source": "roadmap_week8_fixed_scenario",
        "evaluation_role": "scenario_development_not_held_out_week2_benchmark",
        "model_role": "frozen_trained_checkpoint",
        "model": {
            "path": str(checkpoint).replace("\\", "/"),
            "sha256": _sha256(checkpoint),
            "source_model_dir": metadata.get("model_dir", "not stated"),
            "runtime": metadata.get("runtime", {}),
            "model_load_elapsed_seconds": metadata.get("model_load_elapsed_seconds"),
            "inference_elapsed_seconds": metadata.get("inference_elapsed_seconds"),
        },
        "prediction_field": prediction_field,
        "exact_matches": exact_matches,
        "exact_match_denominator": len(rows),
        "exact_match_accuracy": exact_matches / len(rows),
        "field_matches": field_matches,
        "field_denominator": field_denominator,
        "field_accuracy": field_matches / field_denominator,
        "records": rows,
        "research_note": (
            "The fixed scenario is scored against semantics stated by the roadmap. "
            "This two-clause development result does not replace held-out Week 2 evaluation."
        ),
    }


def build_week8_end_to_end_evaluation(
    *,
    simulation: Mapping[str, Any],
    asr_evidence: Mapping[str, Any],
    intent_evaluation: Mapping[str, Any],
    vision_evaluation: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive the five roadmap metrics from stored stage evidence."""

    preparation = simulation.get("preparation", {})
    simulation_result = simulation.get("simulation", {})
    grounding_rows = []
    for clause in preparation.get("clause_results", []):
        clause_id = str(clause.get("clause_id"))
        if clause_id not in EXPECTED_GROUNDING:
            continue
        observed = {
            str(reference.get("location", {}).get("id"))
            for reference in clause.get("effective_grounded_intent", {}).get("references", [])
            if reference.get("status") == "grounded"
        }
        expected = EXPECTED_GROUNDING[clause_id]
        grounding_rows.append(
            {
                "clause_id": clause_id,
                "expected_location_id": expected,
                "observed_location_ids": sorted(observed),
                "matched": expected in observed,
            }
        )
    if len(grounding_rows) != len(EXPECTED_GROUNDING):
        raise ValueError("simulation does not contain both fixed-scenario grounding records")
    schedule = preparation.get("schedule", {})
    schedule_metrics = schedule.get("metrics", {})
    assigned = int(schedule_metrics.get("assigned_tasks", 0))
    total_tasks = int(schedule_metrics.get("total_tasks", 0))
    if total_tasks < 1:
        raise ValueError("simulation schedule has no tasks")
    vision_metrics = vision_evaluation.get("metrics", {})
    detection_value = _required_number(vision_metrics.get("primary_value"), "vision primary metric")
    detection_denominator = int(vision_metrics.get("denominator", 0))
    if detection_denominator < 1:
        raise ValueError("vision metric denominator must be positive")

    stage_timings = {
        "asr_inference_seconds": _required_number(
            asr_evidence.get("inference_elapsed_seconds"), "ASR inference time"
        ),
        "intent_inference_seconds": _required_number(
            intent_evaluation.get("model", {}).get("inference_elapsed_seconds"),
            "intent inference time",
        ),
        "preparation_seconds": _required_number(
            preparation.get("preparation_elapsed_seconds"), "mission preparation time"
        ),
        "simulation_seconds": _required_number(
            simulation_result.get("wall_clock_seconds"), "simulation wall-clock time"
        ),
        "vision_inference_seconds": _required_number(
            vision_evaluation.get("inference", {}).get("elapsed_seconds"),
            "vision inference time",
        ),
    }
    overall_seconds = sum(stage_timings.values())
    exact_denominator = int(intent_evaluation.get("exact_match_denominator", 0))
    if exact_denominator != 2:
        raise ValueError("intent evaluation must contain exactly two roadmap clauses")

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scenario_source": "roadmap_week8_fixed_scenario",
        "status": "completed_software_simulation_evaluation",
        "metrics": {
            "intent_extraction_accuracy": {
                "value": _required_number(
                    intent_evaluation.get("exact_match_accuracy"), "intent exact-match accuracy"
                ),
                "denominator": exact_denominator,
                "definition": "exact structured-intent match across the two fixed roadmap clauses",
                "source_artifact": "outputs/evaluations/week8_exact_scenario_intent_evaluation.json",
            },
            "grounding_accuracy": {
                "value": sum(row["matched"] for row in grounding_rows) / len(grounding_rows),
                "denominator": len(grounding_rows),
                "definition": "resolved destination match against the fixed scenario and operator resolution",
                "source_artifact": "outputs/evaluations/week8_roadmap_scenario_simulation.json",
                "records": grounding_rows,
            },
            "scheduling_quality": {
                "value": assigned / total_tasks,
                "denominator": total_tasks,
                "definition": "task assignment completion ratio; assigned requested task replicas / total replicas",
                "source_artifact": "outputs/evaluations/week8_roadmap_scenario_simulation.json",
                "assigned_tasks": assigned,
            },
            "detection_performance": {
                "value": detection_value,
                "denominator": detection_denominator,
                "definition": str(vision_metrics.get("name", "mission vision primary metric")),
                "source_artifact": "outputs/evaluations/week8_mission_vision_evaluation.json",
                "image_denominator": vision_metrics.get("image_denominator"),
            },
            "overall_execution_time": {
                "value": overall_seconds,
                "denominator": 1,
                "unit": "seconds",
                "definition": (
                    "sum of measured warm-model ASR, intent, mission preparation, deterministic "
                    "simulation, and vision inference wall-clock durations; model loading and "
                    "notebook orchestration overhead excluded"
                ),
                "stage_timings": stage_timings,
            },
        },
        "asr": {
            "word_error_rate": asr_evidence.get("metrics", {}).get("word_error_rate"),
            "exact_match": asr_evidence.get("metrics", {}).get("exact_match"),
        },
        "mission": {
            "simulation_status": simulation_result.get("status"),
            "assignments": len(schedule.get("assignments", [])),
            "safety_status": preparation.get("safety_report", {}).get("status"),
            "telemetry_records": simulation_result.get("telemetry_records"),
        },
        "physical_flight_claimed": False,
        "safety_guarantee_claimed": False,
        "novelty_claimed": False,
        "limitations": [
            "Software simulation only; no physical drones were controlled.",
            "Safety checks validate configured rules and do not guarantee real-world safety.",
            "The two-clause scenario is development evidence, not a statistical end-to-end benchmark.",
            "Agriculture-Vision evaluation uses a disjoint internal validation remainder, not hidden test labels.",
        ],
    }


def render_week8_mission_report(evaluation: Mapping[str, Any]) -> str:
    metrics = evaluation["metrics"]
    lines = [
        "# Week 8 Mission Report",
        "",
        "## Scenario",
        "",
        '"Send two drones north to inspect crops and one drone east to inspect irrigation."',
        "",
        "## Outcome",
        "",
        f"- Status: `{evaluation['status']}`",
        f"- Simulated assignments: `{evaluation['mission']['assignments']}`",
        f"- Safety validator status: `{evaluation['mission']['safety_status']}`",
        f"- Telemetry records: `{evaluation['mission']['telemetry_records']}`",
        "",
        "## Roadmap Metrics",
        "",
    ]
    for name, metric in metrics.items():
        unit = f" {metric['unit']}" if metric.get("unit") else ""
        lines.append(
            f"- `{name}`: `{metric['value']}`{unit} (denominator `{metric['denominator']}`); "
            f"{metric['definition']}"
        )
    lines.extend(["", "## Limits", ""])
    lines.extend(f"- {value}" for value in evaluation.get("limitations", []))
    return "\n".join(lines) + "\n"


def render_week8_demonstration_log(
    simulation: Mapping[str, Any], evaluation: Mapping[str, Any]
) -> str:
    lines = [
        f"scenario_source={evaluation['scenario_source']}",
        f"status={evaluation['status']}",
    ]
    for event in simulation.get("simulation", {}).get("events", []):
        lines.append(
            "time_min={time_min} event={event} drone_id={drone_id} task_id={task_id} phase={phase}".format(
                time_min=event.get("time_min", "not_stated"),
                event=event.get("event", "not_stated"),
                drone_id=event.get("drone_id", "not_stated"),
                task_id=event.get("task_id", "not_stated"),
                phase=event.get("phase", "not_stated"),
            )
        )
    return "\n".join(lines) + "\n"


def _project_intent(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {field: payload.get(field) for field in EVALUATED_INTENT_FIELDS}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_number(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    return float(value)
