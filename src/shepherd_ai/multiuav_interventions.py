"""Draft five-way MultiUAV intervention clusters for human review."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from shepherd_ai.multiuav_context import (
    PRIVILEGED_SOURCE_FIELDS,
    project_agent_visible_context,
    validate_agent_visible_context,
)
from shepherd_ai.multiuav_recoverability import (
    assess_missing_fact,
    assess_resource_conflict,
    extract_explicit_drone_references,
)


VARIANTS = (
    "canonical_execute",
    "official_alias_execute",
    "missing_information_clarify",
    "restored_information_execute",
    "resource_conflict_block",
)
PROPOSED_DECISIONS = {
    "canonical_execute": "EXECUTE",
    "official_alias_execute": "EXECUTE",
    "missing_information_clarify": "CLARIFY",
    "restored_information_execute": "EXECUTE",
    "resource_conflict_block": "BLOCK",
}
PILOT_SEED = "shepherd-multiuav-intervention-pilot-v1"
CASE_INSTRUCTION_SENTINEL = "__CASE_INSTRUCTION__"

_DRONE_REFERENCE_PATTERN = re.compile(
    r"\b(?:drones?\s+)?Drone\s+\d+\b",
    re.IGNORECASE,
)
_INNER_DRONE_REFERENCE_PATTERN = re.compile(r"\bDrone\s+\d+\b", re.IGNORECASE)
_COVERAGE_REWRITES = (
    (
        re.compile(
            r"\bat least\s+(?P<value>\d+(?:\.\d+)?\s*%)\s+of the target area",
            re.IGNORECASE,
        ),
        "the required portion of the target area",
    ),
    (
        re.compile(
            r"\bat least\s+(?P<value>\d+(?:\.\d+)?\s*%)\s+area coverage",
            re.IGNORECASE,
        ),
        "the required level of area coverage",
    ),
    (
        re.compile(
            r"\bexceeds\s+(?P<value>\d+(?:\.\d+)?\s*%)",
            re.IGNORECASE,
        ),
        "exceeds the required threshold",
    ),
)


def select_stratified_training_pilot(
    eligibility_rows: list[dict[str, Any]],
    *,
    per_stratum: int = 2,
    seed: str = PILOT_SEED,
) -> list[dict[str, Any]]:
    """Select a deterministic training-only pilot by scenario/difficulty."""

    if per_stratum < 1:
        raise ValueError("per_stratum must be positive")
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in eligibility_rows:
        if not row.get("eligible") or row.get("split") != "train":
            continue
        key = (str(row["scenario"]), str(row["difficulty"]))
        groups.setdefault(key, []).append(row)
    selected: list[dict[str, Any]] = []
    for key, rows in sorted(groups.items()):
        if len(rows) < per_stratum:
            raise ValueError(f"pilot stratum {key} has fewer than {per_stratum} tasks")
        selected.extend(
            sorted(
                rows,
                key=lambda row: (
                    _rank(seed, str(row["task_id"])),
                    str(row["task_id"]),
                ),
            )[:per_stratum]
        )
    return sorted(selected, key=lambda row: str(row["task_id"]))


def build_draft_cluster(
    session: Mapping[str, Any],
    task: Mapping[str, Any],
    eligibility: Mapping[str, Any],
) -> dict[str, Any]:
    """Create an unreviewed five-case cluster from one eligible source task."""

    if not eligibility.get("eligible"):
        raise ValueError("cannot build a cluster from an ineligible task")
    task_id = str(task["id"])
    if task_id != eligibility.get("task_id"):
        raise ValueError("task and eligibility ids differ")
    canonical = _text(task.get("content"), "canonical instruction")
    alias = _text(eligibility.get("selected_alias"), "selected official alias")
    context = project_agent_visible_context(
        session,
        task_id=task_id,
        instruction=canonical,
    )
    context["instruction"] = CASE_INSTRUCTION_SENTINEL
    validate_agent_visible_context(context)

    references = extract_explicit_drone_references(canonical)
    if references:
        missing, restored, removed_values = _rewrite_drone_identities(canonical)
        missing_fact_kind = "explicit_drone_identity"
        resource_patch = {
            "operation": "remove_required_drones",
            "drone_references": list(references),
        }
    else:
        missing, restored, removed_values = _rewrite_coverage_threshold(canonical)
        missing_fact_kind = "coverage_threshold"
        resource_patch = {
            "operation": "empty_fleet",
            "required_count": 1,
        }
    assessment = assess_missing_fact(missing_fact_kind, context)
    if not assessment.clarification_allowed:
        raise ValueError(f"{task_id}: selected missing fact does not justify CLARIFY")
    conflict_context = apply_context_patch(context, resource_patch)
    if references:
        conflict = assess_resource_conflict(
            conflict_context,
            required_drone_references=references,
        )
    else:
        conflict = assess_resource_conflict(conflict_context, required_count=1)
    if not conflict.block_allowed:
        raise ValueError(f"{task_id}: resource patch does not justify BLOCK")

    context_id = f"{task_id}:base_context"
    cases = [
        _case(task_id, "canonical_execute", canonical, context_id),
        _case(task_id, "official_alias_execute", alias, context_id),
        _case(task_id, "missing_information_clarify", missing, context_id),
        _case(task_id, "restored_information_execute", restored, context_id),
        _case(
            task_id,
            "resource_conflict_block",
            canonical,
            context_id,
            context_patch=resource_patch,
        ),
    ]
    cluster = {
        "cluster_id": f"cluster:{task_id}",
        "source_task_id": task_id,
        "session_id": str(eligibility["session_id"]),
        "split": str(eligibility["split"]),
        "scenario": str(eligibility["scenario"]),
        "difficulty": str(eligibility["difficulty"]),
        "review_status": "pending_human_review",
        "data_status": "template_generated_unreviewed_draft",
        "context": {"context_id": context_id, "payload": context},
        "intervention": {
            "missing_fact_kind": missing_fact_kind,
            "removed_values": removed_values,
            "recoverability": assessment.to_dict(),
            "resource_conflict": conflict.to_dict(),
        },
        "cases": cases,
    }
    validate_draft_cluster(cluster)
    return cluster


def apply_context_patch(
    context: Mapping[str, Any],
    patch: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply the only two allowed unreviewed resource-conflict mutations."""

    result = deepcopy(dict(context))
    operation = patch.get("operation")
    if operation == "remove_required_drones":
        references = patch.get("drone_references")
        if not isinstance(references, list) or not references:
            raise ValueError("remove_required_drones requires references")
        required = {_normalize(str(value)) for value in references}
        result["drones"] = [
            drone
            for drone in result["drones"]
            if _normalize(str(drone.get("name", ""))) not in required
        ]
    elif operation == "empty_fleet":
        if patch.get("required_count") != 1:
            raise ValueError("empty_fleet pilot patch requires required_count=1")
        result["drones"] = []
    else:
        raise ValueError(f"unsupported context patch operation: {operation}")
    validate_agent_visible_context(result)
    return result


def materialize_case_context(
    cluster: Mapping[str, Any],
    case: Mapping[str, Any],
) -> dict[str, Any]:
    """Inject one case instruction and apply only its registered context patch."""

    context_record = cluster.get("context")
    if not isinstance(context_record, Mapping):
        raise ValueError("cluster requires a context record")
    context = deepcopy(dict(context_record["payload"]))
    if context.get("instruction") != CASE_INSTRUCTION_SENTINEL:
        raise ValueError("shared context must contain the case-instruction sentinel")
    context["instruction"] = _text(case.get("instruction"), "case instruction")
    patch = case.get("context_patch")
    if patch is not None:
        if not isinstance(patch, Mapping):
            raise ValueError("case context_patch must be an object")
        context = apply_context_patch(context, patch)
    validate_agent_visible_context(context)
    return context


def validate_draft_cluster(cluster: Mapping[str, Any]) -> None:
    """Reject incomplete, leaking, corrupted, or falsely labelled clusters."""

    cases = cluster.get("cases")
    if not isinstance(cases, list) or len(cases) != len(VARIANTS):
        raise ValueError("draft cluster must contain exactly five cases")
    variants = [case.get("variant") for case in cases]
    if tuple(variants) != VARIANTS:
        raise ValueError("draft cluster variants are incomplete or out of order")
    case_ids = [case.get("case_id") for case in cases]
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("draft cluster case ids must be unique")
    if any(case.get("label_status") != "pending_human_review" for case in cases):
        raise ValueError("draft labels must remain pending human review")
    for case in cases:
        variant = str(case["variant"])
        if case.get("proposed_decision") != PROPOSED_DECISIONS[variant]:
            raise ValueError(f"{variant}: proposed decision does not match protocol")
        instruction = _text(case.get("instruction"), f"{variant} instruction")
        corruption = r"\bdrone\s+the\s+(?:assigned\s+)?(?:drone|uav)\b"
        if re.search(corruption, instruction, re.I):
            raise ValueError(f"{variant}: wording corruption 'drone the drone'")
        if (
            variant
            in {"missing_information_clarify", "restored_information_execute"}
            and re.search(r"\s{2,}", instruction)
        ):
            raise ValueError(f"{variant}: repeated whitespace")

    by_variant = {str(case["variant"]): case for case in cases}
    canonical = by_variant["canonical_execute"]["instruction"]
    missing = by_variant["missing_information_clarify"]["instruction"]
    restored = by_variant["restored_information_execute"]["instruction"]
    if missing == restored or restored == canonical or missing == canonical:
        raise ValueError(
            "missing/restored controls must be distinct from each other and canonical"
        )
    if by_variant["resource_conflict_block"]["instruction"] != canonical:
        raise ValueError("resource conflict must preserve canonical instruction")
    if "context_patch" in by_variant["canonical_execute"]:
        raise ValueError("canonical case must not have a context patch")
    if "context_patch" not in by_variant["resource_conflict_block"]:
        raise ValueError("resource conflict case requires a context patch")

    context_record = cluster.get("context")
    if not isinstance(context_record, Mapping):
        raise ValueError("draft cluster requires one shared context")
    validate_agent_visible_context(context_record["payload"])
    if context_record["payload"].get("instruction") != CASE_INSTRUCTION_SENTINEL:
        raise ValueError("shared context instruction must be a sentinel")
    for case in cases:
        materialized = materialize_case_context(cluster, case)
        if materialized["instruction"] != case["instruction"]:
            raise ValueError("materialized context contains the wrong instruction")
    leaked = _find_forbidden_keys(cluster, PRIVILEGED_SOURCE_FIELDS)
    if leaked:
        raise ValueError(f"draft cluster contains privileged fields: {sorted(leaked)}")


def compact_review_row(cluster: Mapping[str, Any]) -> dict[str, Any]:
    cases = {
        str(case["variant"]): case
        for case in cluster["cases"]
    }
    intervention = cluster["intervention"]
    conflict = intervention["resource_conflict"]
    return {
        "cluster_id": cluster["cluster_id"],
        "source_task_id": cluster["source_task_id"],
        "split": cluster["split"],
        "scenario": cluster["scenario"],
        "difficulty": cluster["difficulty"],
        "missing_fact_kind": intervention["missing_fact_kind"],
        "removed_values": " | ".join(intervention["removed_values"]),
        "canonical_instruction": cases["canonical_execute"]["instruction"],
        "official_alias": cases["official_alias_execute"]["instruction"],
        "missing_instruction": cases["missing_information_clarify"]["instruction"],
        "restored_instruction": cases["restored_information_execute"]["instruction"],
        "resource_conflict_summary": conflict["reason"],
        "automatic_validation": "passed",
        "reviewer_id": "",
        "review_status": "",
        "canonical_valid": "",
        "alias_valid": "",
        "missing_valid": "",
        "restored_valid": "",
        "conflict_valid": "",
        "exclusion_reason": "",
        "reviewer_notes": "",
    }


def validate_unreviewed_pilot_dataset(
    dataset: Mapping[str, Any],
    review_rows: Sequence[Mapping[str, Any]],
    eligibility_rows: Sequence[Mapping[str, Any]],
    source_by_id: Mapping[str, Mapping[str, Any]],
    *,
    expected_per_stratum: int = 2,
) -> dict[str, Any]:
    """Validate the stored pilot against its deterministic source construction."""

    metadata = dataset.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ValueError("pilot dataset requires metadata")
    if metadata.get("split") != "train":
        raise ValueError("pilot dataset must be training-only")
    if metadata.get("data_status") != "template_generated_unreviewed_pilot":
        raise ValueError("pilot dataset has an unexpected data status")
    seed = _text(metadata.get("selection_seed"), "pilot selection seed")
    selected = select_stratified_training_pilot(
        list(eligibility_rows),
        per_stratum=expected_per_stratum,
        seed=seed,
    )
    selected_by_id = {str(row["task_id"]): row for row in selected}

    clusters = dataset.get("clusters")
    if not isinstance(clusters, list):
        raise ValueError("pilot dataset requires a cluster list")
    source_ids = [str(cluster.get("source_task_id")) for cluster in clusters]
    if len(set(source_ids)) != len(source_ids):
        raise ValueError("pilot source task ids must be unique")
    if set(source_ids) != set(selected_by_id):
        raise ValueError("pilot source tasks do not match deterministic selection")
    if set(source_by_id) != set(selected_by_id):
        raise ValueError("source records do not cover the deterministic selection")

    expected_clusters: dict[str, dict[str, Any]] = {}
    for task_id, eligibility in selected_by_id.items():
        source = source_by_id[task_id]
        expected_clusters[task_id] = build_draft_cluster(
            source["session"],
            source["task"],
            eligibility,
        )
    for cluster in clusters:
        validate_draft_cluster(cluster)
        task_id = str(cluster["source_task_id"])
        stored_cluster = json.loads(json.dumps(cluster))
        expected_cluster = json.loads(json.dumps(expected_clusters[task_id]))
        if stored_cluster != expected_cluster:
            raise ValueError(
                f"{task_id}: stored cluster differs from source construction"
            )

    if len(review_rows) != len(clusters):
        raise ValueError("review packet must contain one row per cluster")
    review_by_id: dict[str, Mapping[str, Any]] = {}
    for row in review_rows:
        cluster_id = str(row.get("cluster_id"))
        if cluster_id in review_by_id:
            raise ValueError("review packet cluster ids must be unique")
        review_by_id[cluster_id] = row
    expected_review = {
        str(cluster["cluster_id"]): compact_review_row(cluster)
        for cluster in clusters
    }
    if set(review_by_id) != set(expected_review):
        raise ValueError("review packet cluster ids do not match the dataset")
    for cluster_id, expected_row in expected_review.items():
        if dict(review_by_id[cluster_id]) != expected_row:
            raise ValueError(f"{cluster_id}: review row differs from unreviewed draft")

    strata = Counter(
        f"{cluster['scenario']}|{cluster['difficulty']}" for cluster in clusters
    )
    if len(strata) != 15 or set(strata.values()) != {expected_per_stratum}:
        raise ValueError("pilot does not contain the expected 15 balanced strata")
    return {
        "valid": True,
        "clusters": len(clusters),
        "cases": sum(len(cluster["cases"]) for cluster in clusters),
        "cases_per_cluster": len(VARIANTS),
        "split_counts": dict(Counter(cluster["split"] for cluster in clusters)),
        "stratum_counts": dict(sorted(strata.items())),
        "pending_human_review_clusters": sum(
            cluster["review_status"] == "pending_human_review"
            for cluster in clusters
        ),
        "approved_clusters": 0,
    }


def _case(
    task_id: str,
    variant: str,
    instruction: str,
    context_id: str,
    *,
    context_patch: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    case = {
        "case_id": f"{task_id}:{variant}",
        "variant": variant,
        "instruction": instruction,
        "context_id": context_id,
        "proposed_decision": PROPOSED_DECISIONS[variant],
        "label_status": "pending_human_review",
    }
    if context_patch is not None:
        case["context_patch"] = dict(context_patch)
    return case


def _rewrite_drone_identities(text: str) -> tuple[str, str, list[str]]:
    labels: dict[str, str] = {}
    originals: dict[str, str] = {}

    def replacement(match: re.Match[str], *, restored: bool) -> str:
        inner = _INNER_DRONE_REFERENCE_PATTERN.search(match.group(0))
        if inner is None:
            raise ValueError("drone identity rewrite could not find inner reference")
        original = " ".join(word.capitalize() for word in inner.group(0).split())
        normalized = _normalize(original)
        if normalized not in labels:
            labels[normalized] = _alphabetic_label(len(labels))
            originals[normalized] = original
        generic = f"assigned UAV {labels[normalized]}"
        if match.group(0)[0].isupper():
            generic = f"Assigned UAV {labels[normalized]}"
        return f"{generic} ({original})" if restored else generic

    missing = _DRONE_REFERENCE_PATTERN.sub(
        lambda match: replacement(match, restored=False),
        text,
    )
    restored = _DRONE_REFERENCE_PATTERN.sub(
        lambda match: replacement(match, restored=True),
        text,
    )
    if not labels:
        raise ValueError("instruction has no explicit drone identity")
    return (
        _normalize_whitespace(missing),
        _normalize_whitespace(restored),
        list(originals.values()),
    )


def _rewrite_coverage_threshold(text: str) -> tuple[str, str, list[str]]:
    for pattern, replacement in _COVERAGE_REWRITES:
        match = pattern.search(text)
        if match is None:
            continue
        value = match.group("value")
        missing = f"{text[:match.start()]}{replacement}{text[match.end():]}"
        restored = (
            f"{text[:match.start()]}{replacement} ({value}){text[match.end():]}"
        )
        return (
            _normalize_whitespace(missing),
            _normalize_whitespace(restored),
            [value],
        )
    raise ValueError("generic-drone task has no supported coverage-threshold phrase")


def _alphabetic_label(index: int) -> str:
    if index >= 26:
        raise ValueError("identity template supports at most 26 distinct UAVs")
    return chr(ord("A") + index)


def _find_forbidden_keys(value: Any, forbidden: frozenset[str]) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in forbidden:
                found.add(str(key))
            found.update(_find_forbidden_keys(child, forbidden))
    elif isinstance(value, list):
        for child in value:
            found.update(_find_forbidden_keys(child, forbidden))
    return found


def _rank(seed: str, task_id: str) -> str:
    return hashlib.sha256(f"{seed}\0{task_id}".encode("utf-8")).hexdigest()


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()
