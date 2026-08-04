"""Cluster-aware paired statistics for the MultiUAV study."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
import random
from statistics import fmean
from typing import Any, Iterable, Mapping


BOOTSTRAP_SCHEMA_VERSION = 1
DEFAULT_BOOTSTRAP_SEED = "shepherd-multiuav-cluster-bootstrap-v1"
DEFAULT_BOOTSTRAP_DRAWS = 10_000


def paired_cluster_bootstrap(
    rows: Iterable[Mapping[str, Any]],
    *,
    method_a: str,
    method_b: str,
    metric_field: str = "metric_value",
    expected_variants: int = 5,
    draws: int = DEFAULT_BOOTSTRAP_DRAWS,
    confidence_level: float = 0.95,
    seed: str = DEFAULT_BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Estimate A-minus-B by resampling complete source-task clusters."""

    if not method_a or not method_b or method_a == method_b:
        raise ValueError("method_a and method_b must be distinct non-empty ids")
    if expected_variants < 1:
        raise ValueError("expected_variants must be positive")
    if draws < 1:
        raise ValueError("draws must be positive")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be between zero and one")
    if not seed:
        raise ValueError("bootstrap seed must be non-empty")

    values: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    relevant_count = 0
    for row in rows:
        method_id = str(row.get("method_id", ""))
        if method_id not in {method_a, method_b}:
            continue
        relevant_count += 1
        cluster_id = str(row.get("cluster_id", ""))
        variant = str(row.get("case_variant", ""))
        if not cluster_id or not variant:
            raise ValueError("scored row requires cluster_id and case_variant")
        key = (cluster_id, method_id)
        if variant in values[key]:
            raise ValueError(
                f"duplicate scored row: {cluster_id}/{method_id}/{variant}"
            )
        value = row.get(metric_field)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
        ):
            raise ValueError(f"{metric_field} must be finite numeric")
        values[key][variant] = float(value)
    if relevant_count == 0:
        raise ValueError("no rows exist for the requested methods")

    cluster_ids = sorted({cluster_id for cluster_id, _ in values})
    differences: list[float] = []
    cluster_summaries: list[dict[str, Any]] = []
    for cluster_id in cluster_ids:
        a = values.get((cluster_id, method_a), {})
        b = values.get((cluster_id, method_b), {})
        if (
            len(a) != expected_variants
            or len(b) != expected_variants
            or set(a) != set(b)
        ):
            raise ValueError(
                f"{cluster_id}: complete paired variant set of "
                f"{expected_variants} is required"
            )
        a_mean = fmean(a.values())
        b_mean = fmean(b.values())
        difference = a_mean - b_mean
        differences.append(difference)
        cluster_summaries.append(
            {
                "cluster_id": cluster_id,
                "variant_count": expected_variants,
                "method_a_mean": a_mean,
                "method_b_mean": b_mean,
                "paired_difference": difference,
            }
        )

    generator = random.Random(seed)
    cluster_count = len(differences)
    bootstrap_draws = [
        fmean(differences[generator.randrange(cluster_count)] for _ in range(cluster_count))
        for _ in range(draws)
    ]
    sorted_draws = sorted(bootstrap_draws)
    alpha = 1.0 - confidence_level
    lower = _percentile(sorted_draws, alpha / 2.0)
    upper = _percentile(sorted_draws, 1.0 - alpha / 2.0)
    raw_hash = hashlib.sha256(
        json.dumps(
            bootstrap_draws,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "analysis": {
            "contrast": f"{method_a}_minus_{method_b}",
            "method_a": method_a,
            "method_b": method_b,
            "metric_field": metric_field,
            "point_estimate": fmean(differences),
            "confidence_interval": {
                "method": "percentile_cluster_bootstrap",
                "confidence_level": confidence_level,
                "lower": lower,
                "upper": upper,
            },
            "resampling_unit": "source_task_cluster",
            "cluster_count": cluster_count,
            "cases_per_method_per_cluster": expected_variants,
            "draws": draws,
            "seed": seed,
            "raw_bootstrap_draws_sha256": raw_hash,
        },
        "cluster_summaries": cluster_summaries,
        "raw_bootstrap_draws": bootstrap_draws,
    }


def _percentile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("percentile requires at least one value")
    position = probability * (len(sorted_values) - 1)
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return sorted_values[lower_index]
    fraction = position - lower_index
    return (
        sorted_values[lower_index] * (1.0 - fraction)
        + sorted_values[upper_index] * fraction
    )
