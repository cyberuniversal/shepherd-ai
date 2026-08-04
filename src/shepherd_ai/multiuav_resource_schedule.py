"""Deterministic source-task selection and condition order for resource runs."""

from __future__ import annotations

import hashlib
from typing import Any, Collection, Iterable, Mapping

from shepherd_ai.multiuav_checkpoints import RunConfig
from shepherd_ai.multiuav_model_revisions import REGISTERED_MODEL_REVISIONS
from shepherd_ai.multiuav_prompts import PROMPT_CONTRACT_VERSION


RESOURCE_SELECTION_SEED = "shepherd-multiuav-resource-subset-v1"
RESOURCE_ORDER_SEED = "shepherd-multiuav-resource-condition-order-v1"
RESOURCE_REPETITIONS = (1, 2, 3)
EXPECTED_STRATA = 15
SOURCE_TASKS_PER_STRATUM = 2
APPROVED_DATASET_STATUS = "approved_evaluation_data"


def select_resource_source_tasks(
    eligibility_rows: Iterable[Mapping[str, Any]],
    *,
    supported_task_ids: Collection[str] | None = None,
    seed: str = RESOURCE_SELECTION_SEED,
    split: str = "test",
    per_stratum: int = SOURCE_TASKS_PER_STRATUM,
) -> list[dict[str, Any]]:
    """Select a stable held-out source-task candidate subset by stratum."""

    if not seed:
        raise ValueError("selection seed must be non-empty")
    if per_stratum < 1:
        raise ValueError("per_stratum must be positive")
    supported = None if supported_task_ids is None else set(supported_task_ids)
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    seen_ids: set[str] = set()
    for row in eligibility_rows:
        task_id = str(row.get("task_id", ""))
        if not task_id:
            raise ValueError("eligibility row has no task_id")
        if task_id in seen_ids:
            raise ValueError(f"duplicate eligibility task_id: {task_id}")
        seen_ids.add(task_id)
        if not row.get("eligible") or row.get("split") != split:
            continue
        if supported is not None and task_id not in supported:
            continue
        scenario = str(row.get("scenario", ""))
        difficulty = str(row.get("difficulty", ""))
        if not scenario or not difficulty:
            raise ValueError(f"{task_id}: missing scenario or difficulty")
        groups.setdefault((scenario, difficulty), []).append(row)

    if len(groups) != EXPECTED_STRATA:
        raise ValueError(
            f"resource subset requires {EXPECTED_STRATA} strata; found {len(groups)}"
        )

    selected: list[dict[str, Any]] = []
    for stratum, rows in sorted(groups.items()):
        if len(rows) < per_stratum:
            raise ValueError(
                f"resource stratum {stratum} has fewer than {per_stratum} tasks"
            )
        ranked = sorted(
            rows,
            key=lambda row: (
                _rank(seed, str(row["task_id"])),
                str(row["task_id"]),
            ),
        )
        for row in ranked[:per_stratum]:
            selected.append(
                {
                    "task_id": str(row["task_id"]),
                    "session_id": str(row["session_id"]),
                    "scenario": str(row["scenario"]),
                    "difficulty": str(row["difficulty"]),
                    "split": str(row["split"]),
                    "eligible": bool(row["eligible"]),
                    "selection_rank_sha256": _rank(seed, str(row["task_id"])),
                }
            )
    return sorted(selected, key=lambda row: str(row["task_id"]))


def build_condition_schedule(
    *,
    model_ids: Iterable[str],
    method_ids: Iterable[str],
    repetitions: Iterable[int] = RESOURCE_REPETITIONS,
    seed: str = RESOURCE_ORDER_SEED,
) -> list[dict[str, Any]]:
    """Register one deterministic order for every resource condition."""

    models = _unique_nonempty(model_ids, "model_ids")
    methods = _unique_nonempty(method_ids, "method_ids")
    repetition_values = tuple(sorted(repetitions))
    if repetition_values != RESOURCE_REPETITIONS:
        raise ValueError("resource repetitions must be exactly 1, 2, and 3")
    if not seed:
        raise ValueError("condition-order seed must be non-empty")

    schedule: list[dict[str, Any]] = []
    conditions = sorted((model, method) for model in models for method in methods)
    for repetition in repetition_values:
        ranked = sorted(
            conditions,
            key=lambda condition: (
                _condition_rank(seed, repetition, condition[0], condition[1]),
                condition,
            ),
        )
        for order, (model_id, method_id) in enumerate(ranked, start=1):
            schedule.append(
                {
                    "repetition": repetition,
                    "condition_order": order,
                    "model_id": model_id,
                    "method_id": method_id,
                    "order_rank_sha256": _condition_rank(
                        seed,
                        repetition,
                        model_id,
                        method_id,
                    ),
                }
            )
    return schedule


def build_resource_run_configs(
    condition_schedule: Iterable[Mapping[str, Any]],
    *,
    study_id: str,
    dataset_status: str,
    dataset_sha256: str,
    code_commit: str,
    hardware_protocol_sha256: str,
    resource_schedule_sha256: str,
    decoding: Mapping[str, Any],
) -> list[RunConfig]:
    """Build schedule-bound configs, refusing data without approval status."""

    if dataset_status != APPROVED_DATASET_STATUS:
        raise ValueError("resource run configs require approved evaluation data")
    rows = sorted(
        (dict(row) for row in condition_schedule),
        key=lambda row: (int(row["repetition"]), int(row["condition_order"])),
    )
    if not rows:
        raise ValueError("condition schedule must be non-empty")
    revisions = {
        item.model_id: item.revision for item in REGISTERED_MODEL_REVISIONS
    }
    seen_conditions: set[tuple[str, str, int]] = set()
    orders_by_repetition: dict[int, set[int]] = {}
    configs: list[RunConfig] = []
    for row in rows:
        model_id = str(row["model_id"])
        method_id = str(row["method_id"])
        repetition = int(row["repetition"])
        condition_order = int(row["condition_order"])
        key = (model_id, method_id, repetition)
        if key in seen_conditions:
            raise ValueError(f"duplicate resource condition: {key}")
        seen_conditions.add(key)
        orders = orders_by_repetition.setdefault(repetition, set())
        if condition_order in orders:
            raise ValueError(
                f"duplicate condition order {condition_order} in repetition {repetition}"
            )
        orders.add(condition_order)
        try:
            model_revision = revisions[model_id]
        except KeyError as error:
            raise ValueError(f"unregistered resource model: {model_id}") from error
        run_id = (
            f"{study_id}.resource.r{repetition}.o{condition_order}."
            f"{model_id.rsplit('/', 1)[-1]}.{method_id}"
        )
        config = RunConfig(
            run_id=run_id,
            study_id=study_id,
            run_kind="resource",
            model_id=model_id,
            model_revision=model_revision,
            methods=(method_id,),
            dataset_sha256=dataset_sha256,
            prompt_contract_version=PROMPT_CONTRACT_VERSION,
            decoding=dict(decoding),
            code_commit=code_commit,
            resource_repetition=repetition,
            hardware_protocol_sha256=hardware_protocol_sha256,
            resource_condition_order=condition_order,
            resource_schedule_sha256=resource_schedule_sha256,
        )
        config.validate()
        configs.append(config)

    if set(orders_by_repetition) != set(RESOURCE_REPETITIONS):
        raise ValueError("condition schedule must contain repetitions 1, 2, and 3")
    for repetition, orders in orders_by_repetition.items():
        if orders != set(range(1, len(orders) + 1)):
            raise ValueError(
                f"condition orders for repetition {repetition} must be contiguous"
            )
    return configs


def _unique_nonempty(values: Iterable[str], label: str) -> tuple[str, ...]:
    normalized = tuple(sorted(str(value).strip() for value in values))
    if not normalized or any(not value for value in normalized):
        raise ValueError(f"{label} must be non-empty")
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{label} must be unique")
    return normalized


def _rank(seed: str, task_id: str) -> str:
    return hashlib.sha256(f"{seed}\0{task_id}".encode("utf-8")).hexdigest()


def _condition_rank(
    seed: str,
    repetition: int,
    model_id: str,
    method_id: str,
) -> str:
    value = f"{seed}\0{repetition}\0{model_id}\0{method_id}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
