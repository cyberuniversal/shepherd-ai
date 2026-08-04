"""Fail-closed admission checks for MultiUAV accuracy publication rows."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from shepherd_ai.multiuav_checkpoints import (
    CHECKPOINT_SCHEMA_VERSION,
    RunConfig,
    expected_result_keys,
    result_key,
)


def validate_accuracy_publication_matrix(
    *,
    config: RunConfig,
    rows: Iterable[Mapping[str, Any]],
    expected_case_ids: Iterable[str],
) -> dict[str, Any]:
    """Admit only a complete approved accuracy matrix to later scoring."""

    config.validate()
    if config.run_kind != "accuracy":
        raise ValueError("publication accuracy rows require an accuracy run")
    case_ids = tuple(str(case_id) for case_id in expected_case_ids)
    if not case_ids or any(not case_id for case_id in case_ids):
        raise ValueError("expected_case_ids must be non-empty")
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("expected_case_ids must be unique")

    expected_keys = set(expected_result_keys(case_ids, config.methods))
    materialized = [dict(row) for row in rows]
    observed_keys: set[str] = set()
    parse_error_rows = 0
    for index, row in enumerate(materialized, start=1):
        if row.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
            raise ValueError(f"row {index}: checkpoint schema mismatch")
        if row.get("config_hash") != config.config_hash:
            raise ValueError(f"row {index}: config hash mismatch")
        if row.get("model_id") != config.model_id:
            raise ValueError(f"row {index}: model id mismatch")
        if row.get("model_revision") != config.model_revision:
            raise ValueError(f"row {index}: model revision mismatch")
        case_id = str(row.get("case_id", ""))
        method_id = str(row.get("method_id", ""))
        key = result_key(case_id, method_id)
        if row.get("result_key") != key:
            raise ValueError(f"row {index}: result key mismatch")
        if key in observed_keys:
            raise ValueError(f"row {index}: duplicate result key")
        observed_keys.add(key)
        result = row.get("result")
        if not isinstance(result, Mapping):
            raise ValueError(f"row {index}: result must be an object")
        if result.get("case_id") != case_id or result.get("method_id") != method_id:
            raise ValueError(f"row {index}: nested result identity mismatch")
        if result.get("case_status") != "approved_evaluation_case":
            raise ValueError(f"row {index}: case is not approved evaluation data")
        if result.get("resource_measurement") is not None:
            raise ValueError(f"row {index}: accuracy row contains resource measurement")
        calls = result.get("calls")
        if not isinstance(calls, list) or not calls:
            raise ValueError(f"row {index}: raw model calls are absent")
        final_parse = result.get("final_parse")
        if not isinstance(final_parse, Mapping):
            raise ValueError(f"row {index}: final parse is absent")
        if final_parse.get("parse_status") == "PARSE_ERROR":
            parse_error_rows += 1

    missing = sorted(expected_keys - observed_keys)
    unexpected = sorted(observed_keys - expected_keys)
    if missing or unexpected:
        raise ValueError(
            f"publication matrix mismatch; missing={missing}, unexpected={unexpected}"
        )
    return {
        "valid": True,
        "claim_status": "accuracy_rows_admitted_for_scoring_not_yet_scored",
        "run_kind": config.run_kind,
        "model_id": config.model_id,
        "model_revision": config.model_revision,
        "config_hash": config.config_hash,
        "cases": len(case_ids),
        "methods": list(config.methods),
        "rows": len(materialized),
        "parse_error_rows": parse_error_rows,
        "synthetic_or_resource_rows": 0,
    }
