"""Bounded Week 7 prototype connecting prior module interfaces.

This integration consumes existing ASR and vision artifacts. It does not rerun
the heavy models or claim that a development vision result is a mission image.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from shepherd_ai.clarification_dialogue import ClarificationSession
from shepherd_ai.grounding import MapLocation
from shepherd_ai.integration import run_integrated_workflow
from shepherd_ai.intent import MissionIntent, parse_intent
from shepherd_ai.intent_training import TrainedIntentModel
from shepherd_ai.mission_supervision import MissionSupervisor
from shepherd_ai.safety import SafetyPolicy
from shepherd_ai.scheduling import Assignment, ScheduleResult, load_drones


def run_integrated_prototype(
    input_payload: Mapping[str, Any],
    *,
    intent_system: str,
    locations: Iterable[MapLocation],
    fleet_payload: Mapping[str, Any],
    safety_policy: SafetyPolicy,
    trained_intent_model: TrainedIntentModel | None,
    vision_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    """Run a typed or stored-ASR input through bounded Week 2-7 interfaces."""

    location_list = tuple(locations)
    location_index = {location.id: location for location in location_list}
    normalized_input = _resolve_input(input_payload)
    intent = _resolve_intent(
        normalized_input["command"],
        intent_system,
        trained_intent_model,
    )
    vision = _validate_vision_artifact(vision_artifact)
    workflow = run_integrated_workflow(
        normalized_input["command"],
        locations=location_list,
        fleet_payload=fleet_payload,
        safety_policy=safety_policy,
        mission_altitude_m=safety_policy.default_mission_altitude_m,
        intent_override=intent,
    )
    workflow_payload = workflow.to_dict()
    stages = [
        _stage("speech_or_text_input", "completed", normalized_input["input_type"]),
        _stage(
            "trained_intent_interface" if intent_system == "trained_naive_bayes" else "selected_intent_interface",
            "completed",
            intent.parser,
        ),
        _stage("grounding", "completed" if workflow.grounded_intent else "blocked", workflow.status),
    ]

    if workflow.status == "clarification_required":
        from shepherd_ai.grounding import GroundedIntent, GroundedReference

        grounded = _grounded_intent_from_payload(workflow.grounded_intent, location_index)
        dialogue = ClarificationSession(grounded, location_list)
        stages.append(_stage("clarification", "awaiting_operator", dialogue.snapshot()["status"]))
        return _result(
            workflow.status,
            normalized_input,
            intent,
            workflow_payload,
            stages,
            vision,
            clarification=dialogue.snapshot(),
        )

    stages.extend(
        [
            _stage("planning", "completed" if workflow.mission_plan else "blocked", workflow.status),
            _stage("scheduling", "completed" if workflow.schedule else "blocked", workflow.status),
            _stage("safety", "completed" if workflow.safety_report else "blocked", workflow.status),
        ]
    )
    if workflow.status != "ready_for_simulated_execution" or workflow.schedule is None:
        return _result(
            workflow.status,
            normalized_input,
            intent,
            workflow_payload,
            stages,
            vision,
        )

    vision_binding = _bind_vision_reference(workflow.mission_plan, vision)
    stages.append(_stage("vision_result_binding", "completed", vision_binding["status"]))
    schedule = _schedule_from_payload(workflow.schedule)
    drones = load_drones(fleet_payload, location_index)
    supervisor = MissionSupervisor(
        schedule,
        drones,
        location_index,
        safety_policy,
        mission_altitude_m=safety_policy.default_mission_altitude_m,
    )
    supervisor.confirm_and_start(drones)
    supervision = supervisor.snapshot()
    stages.append(_stage("supervision", "completed", supervision["mission_status"]))
    return _result(
        supervision["mission_status"],
        normalized_input,
        intent,
        workflow_payload,
        stages,
        vision_binding,
        supervision=supervision,
    )


def _resolve_input(payload: Mapping[str, Any]) -> dict[str, Any]:
    input_type = str(payload.get("input_type", ""))
    if input_type == "typed":
        text = str(payload.get("text", "")).strip()
        if not text:
            raise ValueError("typed input requires non-empty text")
        return {"input_type": input_type, "command": text, "record_id": None}
    if input_type == "whisper_prediction":
        prediction = payload.get("prediction")
        if not isinstance(prediction, Mapping):
            raise ValueError("whisper_prediction input requires a prediction object")
        required = ("id", "predicted_transcript", "model_name", "model_version", "parameters")
        missing = [name for name in required if name not in prediction]
        if missing:
            raise ValueError(f"Whisper prediction is missing fields: {', '.join(missing)}")
        command = str(prediction["predicted_transcript"]).strip()
        if not command:
            raise ValueError("Whisper prediction transcript is empty")
        return {
            "input_type": input_type,
            "command": command,
            "record_id": str(prediction["id"]),
            "audio_path": str(prediction.get("audio_path", "")),
            "model_name": str(prediction["model_name"]),
            "model_version": str(prediction["model_version"]),
            "parameters": dict(prediction["parameters"]),
        }
    raise ValueError(f"unsupported integrated input type: {input_type}")


def _resolve_intent(
    command: str,
    intent_system: str,
    trained_model: TrainedIntentModel | None,
) -> MissionIntent:
    if intent_system == "deterministic_primary":
        return parse_intent(command)
    if intent_system == "trained_naive_bayes":
        if trained_model is None:
            raise ValueError("trained_naive_bayes requires a trained intent model")
        return trained_model.predict(command)
    raise ValueError(f"unsupported intent system: {intent_system}")


def _validate_vision_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    if not artifact or not artifact.get("artifact_path") or not artifact.get("scope"):
        raise ValueError("vision artifact requires artifact_path, scope, and payload")
    payload = artifact.get("payload")
    if not isinstance(payload, Mapping) or not payload.get("status") or not payload.get("configuration"):
        raise ValueError("vision artifact payload is not a completed Week 6 result")
    return {
        "artifact_path": str(artifact["artifact_path"]),
        "scope": str(artifact["scope"]),
        "artifact_status": str(payload["status"]),
        "dataset": str(payload["configuration"].get("dataset")),
        "model": str(payload["configuration"].get("model")),
        "metrics": dict(payload.get("post_training_best_checkpoint_validation", {})),
        "research_note": str(payload.get("research_note", "")),
    }


def _bind_vision_reference(
    mission_plan: dict[str, Any] | None,
    vision: dict[str, Any],
) -> dict[str, Any]:
    actions = {
        str(step.get("action"))
        for step in (mission_plan or {}).get("steps", [])
        if isinstance(step, Mapping)
    }
    if "run_vision_model" not in actions:
        raise ValueError("mission plan has no vision step to bind")
    return {
        **vision,
        "status": "development_reference_bound",
        "bound_plan_action": "run_vision_model",
        "mission_specific_observation": False,
        "limitation": (
            "The Week 6 artifact proves the vision interface and prior experiment provenance only; "
            "it is not an observation from this simulated mission."
        ),
    }


def _schedule_from_payload(payload: Mapping[str, Any]) -> ScheduleResult:
    return ScheduleResult(
        strategy=str(payload["strategy"]),
        assignments=tuple(Assignment(**row) for row in payload.get("assignments", [])),
        unassigned_tasks=tuple(str(value) for value in payload.get("unassigned_tasks", [])),
        metrics=dict(payload.get("metrics", {})),
        notes=tuple(str(value) for value in payload.get("notes", [])),
    )


def _grounded_intent_from_payload(
    payload: Mapping[str, Any],
    locations: Mapping[str, MapLocation],
):
    from shepherd_ai.grounding import GroundedIntent, GroundedReference

    references = []
    for row in payload.get("references", []):
        location_payload = row.get("location")
        candidates_payload = row.get("candidates", [])
        references.append(
            GroundedReference(
                field=str(row["field"]),
                phrase=row.get("phrase"),
                status=str(row["status"]),
                location=(
                    locations.get(str(location_payload.get("id")))
                    if isinstance(location_payload, Mapping)
                    else None
                ),
                candidates=tuple(
                    locations[str(candidate["id"])]
                    for candidate in candidates_payload
                    if str(candidate.get("id")) in locations
                ),
                confidence=float(row.get("confidence", 0.0)),
                note=row.get("note"),
            )
        )
    return GroundedIntent(
        intent=dict(payload.get("intent", {})),
        references=tuple(references),
        ready_for_planning=bool(payload.get("ready_for_planning")),
        issues=tuple(str(value) for value in payload.get("issues", [])),
    )


def _stage(name: str, status: str, detail: str) -> dict[str, str]:
    return {"stage": name, "status": status, "detail": detail}


def _result(
    status: str,
    input_payload: dict[str, Any],
    intent: MissionIntent,
    workflow: dict[str, Any],
    stages: list[dict[str, str]],
    vision_binding: dict[str, Any],
    *,
    clarification: dict[str, Any] | None = None,
    supervision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "input": input_payload,
        "intent": intent.to_dict(),
        "workflow": workflow,
        "stages": stages,
        "clarification": clarification,
        "vision_binding": vision_binding,
        "supervision": supervision,
        "limitations": [
            "Software-simulation integration only; no physical drones are controlled.",
            "Stored ASR and vision artifacts are consumed without rerunning their models.",
            "The Week 6 vision binding is not a mission-specific observation.",
        ],
    }
