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
PILOT_SEED = "shepherd-multiuav-intervention-pilot-v2"
CASE_INSTRUCTION_SENTINEL = "__CASE_INSTRUCTION__"
REVIEW_VALIDITY_FIELDS = ("case_valid",)
REVIEW_HUMAN_FIELDS = frozenset(
    {
        "reviewer_id",
        "review_status",
        *REVIEW_VALIDITY_FIELDS,
        "exclusion_reason",
        "reviewer_notes",
    }
)
REVIEW_STATUSES = frozenset(
    {"approved", "needs_revision", "excluded"}
)

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
_TARGET_REFERENCE_PATTERN = re.compile(
    r"\b(?:Fixed|Moving|Circle|Polygon)\s+Target\s+\d+\b"
    r"|\bWaypoint\s+\d+\b",
    re.IGNORECASE,
)
_COORDINATE_PATTERN = re.compile(
    r"\(\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?"
    r"(?:\s*,\s*-?\d+(?:\.\d+)?)?\s*\)"
)


def select_stratified_training_pilot(
    eligibility_rows: list[dict[str, Any]],
    *,
    per_stratum: int = 2,
    seed: str = PILOT_SEED,
    fact_kind_by_task_id: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Select a deterministic training-only pilot by stratum and fact kind."""

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
        ranked = sorted(
            rows,
            key=lambda row: (
                _rank(seed, str(row["task_id"])),
                str(row["task_id"]),
            ),
        )
        chosen: list[dict[str, Any]] = []
        if fact_kind_by_task_id is not None:
            kinds = ("explicit_drone_identity", "coverage_threshold")
            if per_stratum < len(kinds):
                raise ValueError("balanced pilot requires at least two tasks per stratum")
            for kind in kinds:
                candidates = [
                    row
                    for row in ranked
                    if fact_kind_by_task_id.get(str(row["task_id"])) == kind
                ]
                if not candidates:
                    raise ValueError(f"pilot stratum {key} has no {kind} candidate")
                chosen.append(candidates[0])
        chosen_ids = {str(row["task_id"]) for row in chosen}
        chosen.extend(
            row
            for row in ranked
            if str(row["task_id"]) not in chosen_ids
        )
        selected.extend(chosen[:per_stratum])
    return sorted(selected, key=lambda row: str(row["task_id"]))


def classify_intervention_fact_kind(text: str) -> str:
    """Return the supported intervention template for one source instruction."""

    if extract_explicit_drone_references(text):
        return "explicit_drone_identity"
    if any(pattern.search(text) for pattern, _ in _COVERAGE_REWRITES):
        return "coverage_threshold"
    raise ValueError("instruction has no supported intervention fact")


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
    missing_fact_kind = classify_intervention_fact_kind(canonical)
    if missing_fact_kind == "explicit_drone_identity":
        missing, restored, removed_values = _rewrite_drone_identities(canonical)
        resource_patch = {
            "operation": "remove_required_drones",
            "drone_references": list(references),
        }
    else:
        missing, restored, removed_values = _rewrite_coverage_threshold(canonical)
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
    conflict_case = by_variant["resource_conflict_block"]
    conflict_context = materialize_case_context(cluster, conflict_case)
    patch = conflict_case["context_patch"]
    intervention = cluster.get("intervention")
    if not isinstance(intervention, Mapping):
        raise ValueError("draft cluster requires intervention metadata")
    if patch["operation"] == "remove_required_drones":
        expected_references = {
            _normalize(str(value)) for value in intervention["removed_values"]
        }
        patched_references = {
            _normalize(str(value)) for value in patch["drone_references"]
        }
        if patched_references != expected_references:
            raise ValueError("resource conflict patch differs from required UAVs")
        observed_conflict = assess_resource_conflict(
            conflict_context,
            required_drone_references=patch["drone_references"],
        )
    else:
        observed_conflict = assess_resource_conflict(
            conflict_context,
            required_count=patch["required_count"],
        )
    if not observed_conflict.block_allowed:
        raise ValueError("resource conflict patch does not justify BLOCK")
    stored_conflict = json.loads(json.dumps(intervention.get("resource_conflict")))
    recomputed_conflict = json.loads(json.dumps(observed_conflict.to_dict()))
    if stored_conflict != recomputed_conflict:
        raise ValueError("resource conflict metadata differs from applied patch")
    leaked = _find_forbidden_keys(cluster, PRIVILEGED_SOURCE_FIELDS)
    if leaked:
        raise ValueError(f"draft cluster contains privileged fields: {sorted(leaked)}")


def compact_review_rows(cluster: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Create one concise review row per case, never four texts in one row."""

    intervention = cluster["intervention"]
    canonical = next(
        case["instruction"]
        for case in cluster["cases"]
        if case["variant"] == "canonical_execute"
    )
    rows: list[dict[str, Any]] = []
    for case in cluster["cases"]:
        context = materialize_case_context(cluster, case)
        rows.append(
            {
                "case_id": case["case_id"],
                "cluster_id": cluster["cluster_id"],
                "source_task_id": cluster["source_task_id"],
                "split": cluster["split"],
                "scenario": cluster["scenario"],
                "difficulty": cluster["difficulty"],
                "variant": case["variant"],
                "proposed_decision": case["proposed_decision"],
                "instruction": case["instruction"],
                "entity_summary": _entity_summary(canonical, intervention),
                "uav_status_summary": _uav_status_summary(
                    cluster["context"]["payload"], context
                ),
                "intervention_summary": _intervention_summary(case, intervention),
                "automatic_validation": "passed_expected_valid_case_checks",
                "reviewer_id": "",
                "review_status": "",
                "case_valid": "",
                "exclusion_reason": "",
                "reviewer_notes": "",
            }
        )
    return rows


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
    fact_kind_by_task_id = None
    if metadata.get("selection_strategy") == "balanced_fact_kind_per_stratum":
        fact_kind_by_task_id = {
            task_id: classify_intervention_fact_kind(str(source["task"]["content"]))
            for task_id, source in source_by_id.items()
        }
    selected = select_stratified_training_pilot(
        list(eligibility_rows),
        per_stratum=expected_per_stratum,
        seed=seed,
        fact_kind_by_task_id=fact_kind_by_task_id,
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
    if not set(selected_by_id).issubset(source_by_id):
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

    expected_case_count = len(clusters) * len(VARIANTS)
    if len(review_rows) != expected_case_count:
        raise ValueError("review packet must contain one row per case")
    review_by_id: dict[str, Mapping[str, Any]] = {}
    for row in review_rows:
        case_id = str(row.get("case_id"))
        if case_id in review_by_id:
            raise ValueError("review packet case ids must be unique")
        review_by_id[case_id] = row
    expected_review = {
        str(row["case_id"]): row
        for cluster in clusters
        for row in compact_review_rows(cluster)
    }
    if set(review_by_id) != set(expected_review):
        raise ValueError("review packet cluster ids do not match the dataset")
    for case_id, expected_row in expected_review.items():
        if dict(review_by_id[case_id]) != expected_row:
            raise ValueError(f"{case_id}: review row differs from unreviewed draft")

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


def validate_unreviewed_intervention_dataset(
    dataset: Mapping[str, Any],
    review_rows: Sequence[Mapping[str, Any]],
    eligibility_rows: Sequence[Mapping[str, Any]],
    source_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate the complete eligible dataset against pinned source records."""

    metadata = dataset.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ValueError("intervention dataset requires metadata")
    if metadata.get("data_status") != "template_generated_unreviewed_dataset":
        raise ValueError("intervention dataset has an unexpected data status")

    expected_by_id = {
        str(row["task_id"]): row for row in eligibility_rows if row.get("eligible")
    }
    if not expected_by_id:
        raise ValueError("eligibility manifest contains no eligible tasks")
    if set(source_by_id) != set(expected_by_id):
        raise ValueError("source records do not exactly cover eligible tasks")

    clusters = dataset.get("clusters")
    if not isinstance(clusters, list):
        raise ValueError("intervention dataset requires a cluster list")
    source_ids = [str(cluster.get("source_task_id")) for cluster in clusters]
    if len(set(source_ids)) != len(source_ids):
        raise ValueError("intervention dataset source task ids must be unique")
    if set(source_ids) != set(expected_by_id):
        raise ValueError("intervention dataset does not cover every eligible task")

    for cluster in clusters:
        validate_draft_cluster(cluster)
        task_id = str(cluster["source_task_id"])
        source = source_by_id[task_id]
        expected_cluster = build_draft_cluster(
            source["session"],
            source["task"],
            expected_by_id[task_id],
        )
        if json.loads(json.dumps(cluster)) != json.loads(json.dumps(expected_cluster)):
            raise ValueError(
                f"{task_id}: stored cluster differs from source construction"
            )

    expected_review = {
        str(row["case_id"]): row
        for cluster in clusters
        for row in compact_review_rows(cluster)
    }
    if len(review_rows) != len(expected_review):
        raise ValueError("review packet must contain one row per eligible case")
    observed_review: dict[str, Mapping[str, Any]] = {}
    for row in review_rows:
        case_id = str(row.get("case_id"))
        if case_id in observed_review:
            raise ValueError("review packet case ids must be unique")
        observed_review[case_id] = row
    if set(observed_review) != set(expected_review):
        raise ValueError("review packet does not cover every eligible case")
    for case_id, expected_row in expected_review.items():
        if dict(observed_review[case_id]) != expected_row:
            raise ValueError(f"{case_id}: review row differs from unreviewed draft")

    split_counts = Counter(cluster["split"] for cluster in clusters)
    fact_kinds = Counter(
        cluster["intervention"]["missing_fact_kind"] for cluster in clusters
    )
    pending = sum(
        cluster["review_status"] == "pending_human_review"
        for cluster in clusters
    )
    if pending != len(clusters):
        raise ValueError("every generated cluster must remain pending human review")
    return {
        "valid": True,
        "source_tasks_total": len(eligibility_rows),
        "eligible_clusters": len(clusters),
        "excluded_source_tasks": len(eligibility_rows) - len(clusters),
        "cases": len(expected_review),
        "cases_per_cluster": len(VARIANTS),
        "split_cluster_counts": dict(sorted(split_counts.items())),
        "split_case_counts": {
            split: count * len(VARIANTS)
            for split, count in sorted(split_counts.items())
        },
        "missing_fact_kind_counts": dict(sorted(fact_kinds.items())),
        "pending_human_review_clusters": pending,
        "approved_clusters": 0,
    }


def run_validator_negative_controls(
    dataset: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Prove known-bad synthetic mutations are rejected outside study data."""

    clusters = dataset.get("clusters")
    if not isinstance(clusters, list) or not clusters:
        raise ValueError("negative controls require a non-empty pilot dataset")
    probes: list[tuple[str, dict[str, Any]]] = []

    partial = deepcopy(clusters[0])
    partial["cases"].pop()
    probes.append(("partial_cluster", partial))

    identity_source = next(
        (
            cluster
            for cluster in clusters
            if cluster["intervention"]["missing_fact_kind"]
            == "explicit_drone_identity"
        ),
        None,
    )
    if identity_source is None:
        raise ValueError("negative controls require an identity-removal cluster")
    wrong_conflict = deepcopy(identity_source)
    conflict_case = next(
        case
        for case in wrong_conflict["cases"]
        if case["variant"] == "resource_conflict_block"
    )
    conflict_case["context_patch"]["drone_references"] = ["Drone 999"]
    probes.append(("wrong_required_uav_conflict", wrong_conflict))

    results: list[dict[str, Any]] = []
    for probe_id, mutated in probes:
        try:
            validate_draft_cluster(mutated)
        except ValueError as error:
            results.append(
                {
                    "probe_id": probe_id,
                    "data_status": "synthetic_negative_control_not_study_data",
                    "expected": "rejected",
                    "observed": "rejected",
                    "validator_error": str(error),
                }
            )
        else:
            raise AssertionError(f"negative control was accepted: {probe_id}")
    return results


def prepare_pilot_review_rows(
    template_rows: Sequence[Mapping[str, Any]],
    reviewer_id: str,
) -> list[dict[str, Any]]:
    """Create a separate working packet with a project-supplied pseudonym."""

    reviewer = _reviewer_id(reviewer_id)
    prepared: list[dict[str, Any]] = []
    for template in template_rows:
        row = dict(template)
        if any(str(row.get(field, "")).strip() for field in REVIEW_HUMAN_FIELDS):
            raise ValueError("review template already contains human review values")
        row["reviewer_id"] = reviewer
        prepared.append(row)
    return prepared


def normalize_accepted_review_rows(
    review_rows: Sequence[Mapping[str, Any]],
    reviewer_id: str,
) -> list[dict[str, Any]]:
    """Derive formal approvals from reviewer-authored ``Accept:`` notes."""

    reviewer = _reviewer_id(reviewer_id)
    if not review_rows:
        raise ValueError("review response is empty")
    normalized: list[dict[str, Any]] = []
    formal_fields = ("reviewer_id", "review_status", "case_valid", "exclusion_reason")
    for source_row in review_rows:
        row = dict(source_row)
        case_id = str(row.get("case_id", "<unknown>"))
        populated = [
            field for field in formal_fields if str(row.get(field, "")).strip()
        ]
        if populated:
            raise ValueError(
                f"{case_id}: formal review fields already populated: {populated}"
            )
        notes = str(row.get("reviewer_notes", "")).strip()
        if not re.match(r"accept\s*:", notes, flags=re.IGNORECASE):
            raise ValueError(
                f"{case_id}: reviewer_notes must begin with 'Accept:'"
            )
        row.update(
            {
                "reviewer_id": reviewer,
                "review_status": "approved",
                "case_valid": "yes",
                "exclusion_reason": "",
            }
        )
        normalized.append(row)
    return normalized


def validate_completed_pilot_review(
    dataset: Mapping[str, Any],
    review_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate completed human judgments without claiming identity provenance."""

    clusters = dataset.get("clusters")
    if not isinstance(clusters, list) or not clusters:
        raise ValueError("pilot dataset requires non-empty clusters")
    expected_rows = {
        str(row["case_id"]): row
        for cluster in clusters
        for row in compact_review_rows(cluster)
    }
    if len(review_rows) != len(expected_rows):
        raise ValueError("completed review must contain one row per case")

    statuses: Counter[str] = Counter()
    statuses_by_cluster: dict[str, list[str]] = {}
    reviewers: set[str] = set()
    seen: set[str] = set()
    for review_row in review_rows:
        row = dict(review_row)
        case_id = str(row.get("case_id", ""))
        if case_id in seen:
            raise ValueError("completed review case ids must be unique")
        seen.add(case_id)
        if case_id not in expected_rows:
            raise ValueError(f"unknown reviewed case: {case_id}")
        expected = expected_rows[case_id]
        if set(row) != set(expected):
            raise ValueError(f"{case_id}: review packet schema changed")
        for field, expected_value in expected.items():
            if field in REVIEW_HUMAN_FIELDS:
                continue
            if row.get(field) != expected_value:
                raise ValueError(
                    f"{case_id}: immutable review field changed: {field}"
                )

        reviewer = _reviewer_id(str(row.get("reviewer_id", "")))
        reviewers.add(reviewer)
        validity = {
            field: str(row.get(field, "")).strip().lower()
            for field in REVIEW_VALIDITY_FIELDS
        }
        invalid_values = {
            field: value
            for field, value in validity.items()
            if value not in {"yes", "no"}
        }
        if invalid_values:
            raise ValueError(
                f"{case_id}: validity fields must be yes or no: "
                f"{sorted(invalid_values)}"
            )
        status = str(row.get("review_status", "")).strip().lower()
        if status not in REVIEW_STATUSES:
            raise ValueError(f"{case_id}: unsupported review status: {status!r}")
        exclusion_reason = str(row.get("exclusion_reason", "")).strip()
        notes = str(row.get("reviewer_notes", "")).strip()
        rejected_fields = [field for field, value in validity.items() if value == "no"]
        if status == "approved":
            if rejected_fields:
                raise ValueError(
                    f"{case_id}: approved row contains a rejected case"
                )
            if exclusion_reason:
                raise ValueError(
                    f"{case_id}: approved row has an exclusion reason"
                )
        elif status == "needs_revision":
            if not rejected_fields or not notes:
                raise ValueError(
                    f"{case_id}: needs_revision requires a no value and notes"
                )
        elif not exclusion_reason:
            raise ValueError(
                f"{case_id}: excluded row requires an exclusion reason"
            )
        statuses[status] += 1
        statuses_by_cluster.setdefault(str(row["cluster_id"]), []).append(status)

    if seen != set(expected_rows):
        raise ValueError("completed review does not cover every pilot cluster")
    cluster_statuses: Counter[str] = Counter()
    for cluster in clusters:
        cluster_id = str(cluster["cluster_id"])
        case_statuses = statuses_by_cluster.get(cluster_id, [])
        if "excluded" in case_statuses:
            cluster_statuses["excluded"] += 1
        elif "needs_revision" in case_statuses:
            cluster_statuses["needs_revision"] += 1
        else:
            cluster_statuses["approved"] += 1
    return {
        "valid": True,
        "cases_reviewed": len(review_rows),
        "clusters_covered": len(clusters),
        "reviewer_ids": sorted(reviewers),
        "status_counts": dict(sorted(statuses.items())),
        "cluster_status_counts": dict(sorted(cluster_statuses.items())),
        "identity_provenance": "project_attestation_required_not_machine_verifiable",
    }


def _entity_summary(
    canonical: str,
    intervention: Mapping[str, Any],
) -> str:
    drones = extract_explicit_drone_references(canonical)
    drone_text = ", ".join(_display_drone(value) for value in drones) or "generic fleet"
    targets = tuple(dict.fromkeys(match.group(0) for match in _TARGET_REFERENCE_PATTERN.finditer(canonical)))
    coordinates = tuple(dict.fromkeys(match.group(0) for match in _COORDINATE_PATTERN.finditer(canonical)))
    parts = [f"UAVs={drone_text}"]
    if targets:
        parts.append(f"targets={_summarize_values(targets)}")
    if coordinates:
        parts.append(f"coordinates={_summarize_values(coordinates)}")
    parts.append(
        "removed=" + _summarize_values(tuple(str(value) for value in intervention["removed_values"]))
    )
    return "; ".join(parts)


def _uav_status_summary(
    base_context: Mapping[str, Any],
    case_context: Mapping[str, Any],
) -> str:
    return f"base {_fleet_summary(base_context)}; case {_fleet_summary(case_context)}"


def _fleet_summary(context: Mapping[str, Any]) -> str:
    drones = context["drones"]
    statuses = Counter(str(drone.get("status", "unknown")) for drone in drones)
    status_text = ",".join(f"{key}={value}" for key, value in sorted(statuses.items()))
    return f"fleet={len(drones)}" + (f" ({status_text})" if status_text else "")


def _intervention_summary(
    case: Mapping[str, Any],
    intervention: Mapping[str, Any],
) -> str:
    variant = str(case["variant"])
    removed = _summarize_values(tuple(str(value) for value in intervention["removed_values"]))
    if variant == "canonical_execute":
        return "unchanged canonical instruction"
    if variant == "official_alias_execute":
        return "official source alias; no context mutation"
    if variant == "missing_information_clarify":
        return f"removed {intervention['missing_fact_kind']}: {removed}"
    if variant == "restored_information_execute":
        return f"restored {intervention['missing_fact_kind']}: {removed}"
    conflict = intervention["resource_conflict"]
    missing = conflict.get("missing_required_drones") or ()
    if missing:
        detail = "removed required UAVs=" + _summarize_values(
            tuple(_display_drone(str(value)) for value in missing)
        )
    else:
        detail = f"required fleet={conflict['required_count']}; visible fleet=0"
    return f"irrecoverable fleet conflict; {detail}; proposed BLOCK"


def _summarize_values(values: Sequence[str], *, limit: int = 4) -> str:
    shown = list(values[:limit])
    suffix = f" (+{len(values) - limit} more)" if len(values) > limit else ""
    return " | ".join(shown) + suffix


def _display_drone(value: str) -> str:
    match = re.fullmatch(r"drone\s+(\d+)", value, re.IGNORECASE)
    return f"Drone {match.group(1)}" if match else value


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


def _reviewer_id(value: str) -> str:
    reviewer = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", reviewer):
        raise ValueError(
            "reviewer_id must be a 1-64 character project-supplied pseudonym"
        )
    return reviewer
