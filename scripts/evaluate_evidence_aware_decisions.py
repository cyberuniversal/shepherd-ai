"""Evaluate Shepherd-AI evidence gates against a one-stage actionability baseline."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.clarification_dialogue import ClarificationSession  # noqa: E402
from shepherd_ai.evidence_evaluation import (  # noqa: E402
    score_clarification_recovery,
    score_decision_rows,
    workflow_status_to_decision,
)
from shepherd_ai.grounding import ground_intent, load_map_locations  # noqa: E402
from shepherd_ai.grounding_clarification import build_clarification_report  # noqa: E402
from shepherd_ai.integration import run_integrated_workflow  # noqa: E402
from shepherd_ai.intent import parse_intent  # noqa: E402
from shepherd_ai.safety import load_safety_policy  # noqa: E402
from shepherd_ai.week8_pipeline import prepare_week8_mission  # noqa: E402


DEFAULT_GROUNDING_CASES = ROOT / "datasets" / "maps" / "human_grounding_benchmark_v1.jsonl"
DEFAULT_SAFETY_CASES = ROOT / "datasets" / "safety" / "week7_safety_cases_v1.jsonl"
DEFAULT_DIALOGUE_CASES = ROOT / "datasets" / "safety" / "week7_clarification_cases_v1.jsonl"
DEFAULT_CONFLICT_CASES = ROOT / "datasets" / "evidence" / "week9_conflict_cases_v1.jsonl"
DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_FLEET = ROOT / "datasets" / "drones" / "week5_three_drone_fleet_v1.json"
DEFAULT_POLICY = ROOT / "datasets" / "safety" / "week7_safety_policy_v1.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "evaluations" / "week9_evidence_aware_decisions_v1.json"
DEFAULT_REPORT = ROOT / "reports" / "week9_evidence_aware_decisions_v1.md"
SYSTEMS = (
    "shepherd_evidence_aware_v1",
    "single_pass_actionability_baseline_v1",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grounding-cases", type=Path, default=DEFAULT_GROUNDING_CASES)
    parser.add_argument("--safety-cases", type=Path, default=DEFAULT_SAFETY_CASES)
    parser.add_argument("--dialogue-cases", type=Path, default=DEFAULT_DIALOGUE_CASES)
    parser.add_argument("--conflict-cases", type=Path, default=DEFAULT_CONFLICT_CASES)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--fleet", type=Path, default=DEFAULT_FLEET)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--strategy", default="least_loaded")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    locations = load_map_locations(args.map)
    fleet = _read_json(args.fleet)
    policy = load_safety_policy(args.policy)
    decision_rows = [
        *_evaluate_grounding_cases(_read_jsonl(args.grounding_cases), locations),
        *_evaluate_safety_cases(
            _read_jsonl(args.safety_cases),
            locations,
            fleet,
            policy,
            strategy=args.strategy,
        ),
        *_evaluate_conflict_cases(
            _read_jsonl(args.conflict_cases),
            locations,
            fleet,
            policy,
            strategy=args.strategy,
        ),
    ]
    dialogue_rows = _evaluate_dialogue_cases(_read_jsonl(args.dialogue_cases), locations)
    recovery_rows = [
        *dialogue_rows,
        *[
            {
                "case_id": row["case_id"],
                "recovery_attempted": row.get("recovery_attempted", False),
                "recovery_succeeded": (
                    row.get("recovery_attempted") is True
                    and row["systems"]["shepherd_evidence_aware_v1"] == "proceed"
                ),
            }
            for row in decision_rows
            if row["stratum"] == "conflicting_grounded_references"
        ],
    ]
    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "evaluator": "week9_evidence_aware_decision_evaluator_v1",
            "python_version": platform.python_version(),
            "random_seed": None,
            "strategy": args.strategy,
            "systems": list(SYSTEMS),
            "input_paths": {
                "grounding_cases": _repo_path(args.grounding_cases),
                "safety_cases": _repo_path(args.safety_cases),
                "dialogue_cases": _repo_path(args.dialogue_cases),
                "conflict_cases": _repo_path(args.conflict_cases),
                "map": _repo_path(args.map),
                "fleet": _repo_path(args.fleet),
                "policy": _repo_path(args.policy),
            },
            "input_sha256": {
                name: _sha256(path)
                for name, path in {
                    "grounding_cases": args.grounding_cases,
                    "safety_cases": args.safety_cases,
                    "dialogue_cases": args.dialogue_cases,
                    "conflict_cases": args.conflict_cases,
                    "map": args.map,
                    "fleet": args.fleet,
                    "policy": args.policy,
                }.items()
            },
            "data_scope": {
                "grounding": "existing_human_written_holdout_commands",
                "safety": "existing_synthetic_development_cases",
                "conflict": "synthetic_controlled_cases",
                "dialogue": "existing_synthetic_stateful_dialogue_cases",
            },
            "baseline_definition": (
                "A deterministic one-stage command-only baseline that proceeds whenever the "
                "existing parser identifies an action. It receives no map, fleet, policy, or "
                "intermediate evidence. It is an ablation, not TACOS and not an LLM result."
            ),
            "research_note": (
                "This is a controlled mixed-source diagnostic. Only the grounding stratum uses "
                "human-written commands. Safety, conflict, and dialogue results are synthetic and "
                "must not be presented as real-world reliability."
            ),
            "metric_semantics": (
                "silent_misexecution_rate is a decision-level proxy: it counts proceed decisions "
                "on gold clarify/block cases, without executing those incorrectly advanced missions."
            ),
        },
        "summary": {
            "decision_cases": len(decision_rows),
            "dialogue_cases": len(dialogue_rows),
            "systems": {
                system: _score_system(decision_rows, system)
                for system in SYSTEMS
            },
            "clarification_recovery": score_clarification_recovery(recovery_rows),
            "dialogue_terminal_status_accuracy": _ratio(
                sum(row["status_matches_expected"] for row in dialogue_rows),
                len(dialogue_rows),
            ),
        },
        "strata": {
            stratum: {
                system: _score_system(
                    [row for row in decision_rows if row["stratum"] == stratum],
                    system,
                )
                for system in SYSTEMS
            }
            for stratum in sorted({row["stratum"] for row in decision_rows})
        },
        "decision_cases": decision_rows,
        "clarification_cases": dialogue_rows,
        "claim_limits": {
            "monolithic_llm_baseline_evaluated": False,
            "tacos_reimplementation_evaluated": False,
            "human_factors_evaluated": False,
            "physical_flight_evaluated": False,
            "real_world_reliability_claimed": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text(_render_report(payload), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    print(f"Wrote {args.output}")
    print(f"Wrote {args.report_output}")


def _evaluate_grounding_cases(
    cases: Iterable[dict[str, Any]],
    locations: Any,
) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        expected_statuses = {
            str(value["status"])
            for value in dict(case["expected_grounding"]).values()
        }
        expected = (
            "clarify"
            if expected_statuses & {"ambiguous", "unresolved"}
            else "proceed"
        )
        intent = parse_intent(str(case["text"]))
        clarification = build_clarification_report(ground_intent(intent, locations))
        predicted = "clarify" if clarification.blocks_planning else "proceed"
        rows.append(
            _decision_row(
                case_id=str(case["id"]),
                stratum="human_written_grounding_sufficiency",
                data_type=str(case["data_type"]),
                command=str(case["text"]),
                expected=expected,
                shepherd=predicted,
                baseline=_actionability_baseline(str(case["text"])),
                notes=[f"source={case['source']}", f"split={case['split']}"],
            )
        )
    return rows


def _evaluate_safety_cases(
    cases: Iterable[dict[str, Any]],
    locations: Any,
    fleet: dict[str, Any],
    policy: Any,
    *,
    strategy: str,
) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        scheduling_fleet = _set_all_drones(fleet, case.get("scheduling_fleet_set_all"))
        current_fleet = _set_all_drones(scheduling_fleet, case.get("current_fleet_set_all"))
        result = run_integrated_workflow(
            str(case["command"]),
            locations=locations,
            fleet_payload=scheduling_fleet,
            current_fleet_payload=current_fleet,
            safety_policy=policy,
            strategy=strategy,
            mission_altitude_m=case.get("mission_altitude_m"),
        )
        expected = workflow_status_to_decision(str(case["expected_workflow_status"]))
        rows.append(
            _decision_row(
                case_id=str(case["case_id"]),
                stratum="synthetic_preflight_evidence",
                data_type="synthetic_week7_safety_evaluation_case",
                command=str(case["command"]),
                expected=expected,
                shepherd=workflow_status_to_decision(result.status),
                baseline=_actionability_baseline(str(case["command"])),
                notes=list(case.get("notes", [])),
                actual_workflow_status=result.status,
            )
        )
    return rows


def _evaluate_conflict_cases(
    cases: Iterable[dict[str, Any]],
    locations: Any,
    fleet: dict[str, Any],
    policy: Any,
    *,
    strategy: str,
) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        result = prepare_week8_mission(
            str(case["command"]),
            locations=locations,
            fleet_payload=fleet,
            safety_policy=policy,
            strategy=strategy,
            grounding_resolutions=dict(case.get("grounding_resolutions", {})),
        )
        row = _decision_row(
            case_id=str(case["case_id"]),
            stratum="conflicting_grounded_references",
            data_type="synthetic_week9_conflict_case",
            command=str(case["command"]),
            expected=str(case["expected_decision"]),
            shepherd=workflow_status_to_decision(str(result["status"])),
            baseline=_actionability_baseline(str(case["command"])),
            notes=list(case.get("notes", [])),
            actual_workflow_status=str(result["status"]),
        )
        row["recovery_attempted"] = case.get("recovery_attempted", False)
        rows.append(row)
    return rows


def _evaluate_dialogue_cases(
    cases: Iterable[dict[str, Any]],
    locations: Any,
) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        session = ClarificationSession(
            ground_intent(parse_intent(str(case["command"])), locations),
            locations,
        )
        for event in case.get("events", []):
            event_type = str(event.get("type"))
            if event_type == "choose":
                session.submit_choices(
                    {
                        str(key): str(value)
                        for key, value in dict(event.get("choices", {})).items()
                    }
                )
            elif event_type == "confirm":
                session.confirm()
            elif event_type == "cancel":
                session.cancel(str(event.get("reason", "operator_cancelled")))
            elif event_type == "timeout":
                session.timeout()
            else:
                raise ValueError(f"unsupported clarification event: {event_type}")
        result = session.snapshot()
        expected = str(case["expected_status"])
        rows.append(
            {
                "case_id": str(case["case_id"]),
                "data_type": "synthetic_week7_stateful_clarification_case",
                "expected_status": expected,
                "actual_status": result["status"],
                "status_matches_expected": result["status"] == expected,
                "recovery_attempted": expected == "confirmed",
                "recovery_succeeded": result["status"] == "confirmed",
                "notes": list(case.get("notes", [])),
            }
        )
    return rows


def _decision_row(
    *,
    case_id: str,
    stratum: str,
    data_type: str,
    command: str,
    expected: str,
    shepherd: str,
    baseline: str,
    notes: list[str],
    actual_workflow_status: str | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "stratum": stratum,
        "data_type": data_type,
        "command": command,
        "expected_decision": expected,
        "systems": {
            "shepherd_evidence_aware_v1": shepherd,
            "single_pass_actionability_baseline_v1": baseline,
        },
        "actual_workflow_status": actual_workflow_status,
        "notes": notes,
    }


def _score_system(rows: list[dict[str, Any]], system: str) -> dict[str, Any]:
    return score_decision_rows(
        [
            {
                "expected_decision": row["expected_decision"],
                "predicted_decision": row["systems"][system],
            }
            for row in rows
        ]
    )


def _actionability_baseline(command: str) -> str:
    return "proceed" if parse_intent(command).action is not None else "clarify"


def _set_all_drones(payload: dict[str, Any], updates: Any) -> dict[str, Any]:
    result = deepcopy(payload)
    if updates is None:
        return result
    if not isinstance(updates, dict):
        raise ValueError("fleet set-all updates must be an object")
    for drone in result.get("drones", []):
        drone.update(updates)
    return result


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


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    shepherd = summary["systems"]["shepherd_evidence_aware_v1"]
    baseline = summary["systems"]["single_pass_actionability_baseline_v1"]
    recovery = summary["clarification_recovery"]
    lines = [
        "# Evidence-Aware Decision Evaluation",
        "",
        "This controlled diagnostic combines a human-written grounding stratum with "
        "synthetic safety, conflict, and dialogue strata. It is not a real-world "
        "reliability estimate.",
        "",
        "## Results",
        "",
        "| System | Decision accuracy | False refusal rate | Silent-proceed proxy rate | Clarification recall | Block recall |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        _metric_row("Shepherd evidence-aware", shepherd),
        _metric_row("Single-pass actionability baseline", baseline),
        "",
        f"- Clarification recovery: `{recovery['successful_recoveries']}/"
        f"{recovery['recovery_attempts']}` "
        f"(`{_format_metric(recovery['clarification_recovery_rate'])}`).",
        f"- Dialogue terminal-status accuracy: "
        f"`{_format_metric(summary['dialogue_terminal_status_accuracy'])}` "
        f"over `{summary['dialogue_cases']}` synthetic cases.",
        "",
        "## Interpretation",
        "",
        "The comparison isolates the behavior of explicit evidence gates against a "
        "command-only proceed-if-actionable ablation. The baseline has no map, fleet, "
        "policy, or intermediate evidence, so this is not a fair substitute for a "
        "strong monolithic LLM baseline. It measures the failure mode created by "
        "removing evidence checks.",
        "",
        "## Claim Limits",
        "",
        "- No monolithic LLM or TACOS reimplementation was evaluated.",
        "- Silent misexecution is a decision-level proxy; incorrect missions were not executed.",
        "- Safety, conflict, and dialogue strata are synthetic.",
        "- Dialogue recovery measures deterministic state handling, not usability.",
        "- No physical flight or real-world reliability claim is supported.",
    ]
    return "\n".join(lines) + "\n"


def _metric_row(label: str, metrics: dict[str, Any]) -> str:
    return (
        f"| {label} | {_format_metric(metrics['decision_accuracy'])} | "
        f"{_format_metric(metrics['false_refusal_rate'])} | "
        f"{_format_metric(metrics['silent_misexecution_rate'])} | "
        f"{_format_metric(metrics['clarification_recall'])} | "
        f"{_format_metric(metrics['block_recall'])} |"
    )


def _format_metric(value: float | None) -> str:
    return "not evaluated" if value is None else f"{value:.4f}"


if __name__ == "__main__":
    main()
