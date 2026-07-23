"""Build label-separated inputs for the Week 9 monolithic decision baseline."""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
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
from shepherd_ai.monolithic_decision import (  # noqa: E402
    PROMPT_VERSION,
    build_messages,
    messages_sha256,
    validate_input_record,
)


DEFAULT_EVALUATION = ROOT / "outputs" / "evaluations" / "week9_evidence_aware_decisions_v1.json"
DEFAULT_SAFETY_CASES = ROOT / "datasets" / "safety" / "week7_safety_cases_v1.jsonl"
DEFAULT_CONFLICT_CASES = ROOT / "datasets" / "evidence" / "week9_conflict_cases_v1.jsonl"
DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_FLEET = ROOT / "datasets" / "drones" / "week5_three_drone_fleet_v1.json"
DEFAULT_POLICY = ROOT / "datasets" / "safety" / "week7_safety_policy_v1.json"
DEFAULT_INPUTS = ROOT / "outputs" / "evaluations" / "week9_monolithic_diagnostic_inputs_v1.jsonl"
DEFAULT_GOLD = ROOT / "datasets" / "evidence" / "week9_monolithic_diagnostic_gold_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "outputs" / "evaluations" / "week9_monolithic_diagnostic_manifest_v1.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", type=Path, default=DEFAULT_EVALUATION)
    parser.add_argument("--safety-cases", type=Path, default=DEFAULT_SAFETY_CASES)
    parser.add_argument("--conflict-cases", type=Path, default=DEFAULT_CONFLICT_CASES)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--fleet", type=Path, default=DEFAULT_FLEET)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--inputs-output", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--gold-output", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--manifest-output", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()

    evaluation = _read_json(args.evaluation)
    safety_cases = {
        str(row["case_id"]): row for row in _read_jsonl(args.safety_cases)
    }
    conflict_cases = {
        str(row["case_id"]): row for row in _read_jsonl(args.conflict_cases)
    }
    map_records = [
        {
            "id": location.id,
            "name": location.name,
            "category": location.category,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "radius_m": location.radius_m,
            "map_role": location.map_role,
            "flyable": location.flyable,
            "requires_clearance": location.requires_clearance,
            "aliases": list(location.aliases),
        }
        for location in load_map_locations(args.map)
    ]
    base_fleet = _read_json(args.fleet)
    policy = _read_json(args.policy)

    inputs: list[dict[str, Any]] = []
    gold: list[dict[str, Any]] = []
    for row in evaluation.get("decision_cases", []):
        case_id = str(row["case_id"])
        stratum = str(row["stratum"])
        record = _build_input(
            row,
            map_records=map_records,
            base_fleet=base_fleet,
            policy=policy,
            safety_case=safety_cases.get(case_id),
            conflict_case=conflict_cases.get(case_id),
        )
        messages = build_messages(record)
        input_record = {
            **record,
            "prompt_version": PROMPT_VERSION,
            "messages": messages,
            "prompt_sha256": messages_sha256(messages),
        }
        validate_input_record(input_record)
        inputs.append(input_record)
        gold.append(
            {
                "case_id": case_id,
                "stratum": stratum,
                "data_type": str(row["data_type"]),
                "expected_decision": str(row["expected_decision"]),
                "shepherd_decision": str(
                    row["systems"]["shepherd_evidence_aware_v1"]
                ),
                "source_evaluation": _repo_path(args.evaluation),
            }
        )

    _validate_unique_ids(inputs)
    _validate_unique_ids(gold)
    _write_jsonl(inputs, args.inputs_output)
    _write_jsonl(gold, args.gold_output)
    source_paths = {
        "evaluation": args.evaluation,
        "safety_cases": args.safety_cases,
        "conflict_cases": args.conflict_cases,
        "map": args.map,
        "fleet": args.fleet,
        "policy": args.policy,
    }
    manifest = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "builder": "week9_monolithic_decision_packet_builder_v1",
            "python_version": platform.python_version(),
            "prompt_version": PROMPT_VERSION,
            "random_seed": None,
            "research_role": "diagnostic_not_fresh_human_heldout",
        },
        "case_count": len(inputs),
        "stratum_counts": dict(
            sorted(Counter(str(row["stratum"]) for row in gold).items())
        ),
        "gold_decision_counts": dict(
            sorted(Counter(str(row["expected_decision"]) for row in gold).items())
        ),
        "inputs": {
            "path": _repo_path(args.inputs_output),
            "sha256": _sha256(args.inputs_output),
            "contains_gold_labels": False,
        },
        "gold": {
            "path": _repo_path(args.gold_output),
            "sha256": _sha256(args.gold_output),
            "loaded_by_model_runner": False,
        },
        "sources": {
            name: {"path": _repo_path(path), "sha256": _sha256(path)}
            for name, path in source_paths.items()
        },
        "leakage_controls": [
            "Model input JSONL contains no expected_decision or Shepherd decision.",
            "Gold labels are stored in a separate JSONL not accepted by the model runner.",
            "Each exact message list has a SHA-256 recorded before inference.",
            "This packet reuses development evidence and is not called held-out.",
        ],
    }
    args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "case_count": len(inputs),
                "inputs": str(args.inputs_output),
                "gold": str(args.gold_output),
                "manifest": str(args.manifest_output),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _build_input(
    row: dict[str, Any],
    *,
    map_records: list[dict[str, Any]],
    base_fleet: dict[str, Any],
    policy: dict[str, Any],
    safety_case: dict[str, Any] | None,
    conflict_case: dict[str, Any] | None,
) -> dict[str, Any]:
    case_id = str(row["case_id"])
    common = {
        "case_id": case_id,
        "stratum": str(row["stratum"]),
        "data_type": str(row["data_type"]),
        "command": str(row["command"]),
    }
    if row["stratum"] == "human_written_grounding_sufficiency":
        return {
            **common,
            "decision_stage": "grounding_sufficiency",
            "stage_definition": (
                "Decide only whether every supplied location or target reference "
                "resolves uniquely against the map. Do not apply flight-safety policy."
            ),
            "evidence": {"map_records": map_records},
        }
    if row["stratum"] == "synthetic_preflight_evidence":
        if safety_case is None:
            raise ValueError(f"{case_id}: missing registered safety case")
        scheduling_fleet = _set_all_drones(
            base_fleet, safety_case.get("scheduling_fleet_set_all")
        )
        current_fleet = _set_all_drones(
            scheduling_fleet, safety_case.get("current_fleet_set_all")
        )
        return {
            **common,
            "decision_stage": "preflight",
            "stage_definition": (
                "Decide whether this mission may advance to simulated execution. "
                "Clarify unresolved map references; block policy or fleet violations."
            ),
            "evidence": {
                "map_records": map_records,
                "scheduling_fleet": scheduling_fleet,
                "current_fleet": current_fleet,
                "safety_policy": policy,
                "mission_altitude_m": safety_case.get("mission_altitude_m"),
            },
        }
    if row["stratum"] == "conflicting_grounded_references":
        if conflict_case is None:
            raise ValueError(f"{case_id}: missing registered conflict case")
        return {
            **common,
            "decision_stage": "compound_grounding_and_preflight",
            "stage_definition": (
                "Resolve each compound clause to one destination. Clarify inconsistent "
                "location and target references unless a valid operator resolution is supplied; "
                "then apply fleet and policy evidence."
            ),
            "evidence": {
                "map_records": map_records,
                "fleet": base_fleet,
                "safety_policy": policy,
                "operator_grounding_resolutions": dict(
                    conflict_case.get("grounding_resolutions", {})
                ),
            },
        }
    raise ValueError(f"{case_id}: unsupported stratum {row['stratum']!r}")


def _set_all_drones(payload: dict[str, Any], updates: Any) -> dict[str, Any]:
    result = deepcopy(payload)
    if updates is None:
        return result
    if not isinstance(updates, dict):
        raise ValueError("fleet set-all updates must be an object")
    for drone in result.get("drones", []):
        drone.update(updates)
    return result


def _validate_unique_ids(rows: list[dict[str, Any]]) -> None:
    ids = [str(row["case_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("case IDs must be unique")


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


def _write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return str(resolved)


if __name__ == "__main__":
    main()
