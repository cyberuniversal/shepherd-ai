from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from shepherd_ai.multiuav_resource_analysis import (
    analyze_resource_metric_rows,
    derive_resource_metric_row,
    validate_resource_analysis_boundary,
    write_derived_resource_rows_archive,
)


METHODS = (
    "M1_monolithic",
    "M2_post_plan_deterministic",
    "M3_stage_wise",
    "M4_post_plan_compute_matched",
)
VARIANTS = (
    "canonical_execute",
    "official_alias_execute",
    "missing_information_clarify",
    "restored_information_execute",
    "resource_conflict_block",
)
INFERENTIAL_METRICS = (
    "method_case_duration_seconds",
    "input_tokens",
    "output_tokens",
    "model_call_count",
    "process_ram_peak_bytes",
    "board_vram_peak_bytes",
    "process_vram_peak_bytes",
    "gpu_board_energy_joules",
)
DIAGNOSTICS = (
    "gpu_utilization_peak_percent",
    "temperature_peak_celsius",
)


def _raw_row(*, case_id: str = "task-1:canonical_execute") -> dict:
    return {
        "schema_version": 3,
        "config_hash": "a" * 64,
        "result_key": "b" * 64,
        "case_id": case_id,
        "method_id": "M3_stage_wise",
        "model_id": "Qwen/Qwen2.5-3B-Instruct",
        "model_revision": "aa8e72537993ba99e69dfaafa59ed015b17504d1",
        "result": {
            "case_id": case_id,
            "method_id": "M3_stage_wise",
            "actual_model_call_count": 2,
            "calls": [
                {
                    "request": {"messages": ["must not be copied"]},
                    "generation": {
                        "input_tokens": 10,
                        "output_tokens": 4,
                        "latency_ms": 20.0,
                        "raw_output": "must not be copied",
                    },
                },
                {
                    "request": {"messages": ["must not be copied"]},
                    "generation": {
                        "input_tokens": 12,
                        "output_tokens": 5,
                        "latency_ms": 30.0,
                        "raw_output": "must not be copied",
                    },
                },
            ],
            "resource_measurement": {
                "valid": True,
                "duration_seconds": 0.5,
                "process_ram": {"maximum": 1000},
                "board_vram": {"maximum": 2000},
                "process_vram": {"maximum": 1500},
                "gpu_utilization_percent": {"maximum": 90},
                "temperature_celsius": {"maximum": 55},
                "energy": {
                    "scope": "nvidia_gpu_board_only",
                    "joules": 12.5,
                },
            },
        },
    }


def _spec(*, clusters: int = 2, repetitions: int = 1, draws: int = 100) -> dict:
    metrics = [
        {
            "metric_id": metric,
            "unit": "unit",
            "direction": "lower_is_less_resource_intensive",
            "role": "secondary_resource_outcome",
        }
        for metric in INFERENTIAL_METRICS
    ]
    metrics.extend(
        {
            "metric_id": metric,
            "unit": "unit",
            "direction": "diagnostic_no_preferred_direction",
            "role": "resource_diagnostic",
        }
        for metric in DIAGNOSTICS
    )
    return {
        "analysis_version": "multiuav_resource_analysis_v1",
        "scope": {
            "source_task_clusters": clusters,
            "variants_per_cluster": 5,
            "models": 1,
            "methods": 4,
            "repetitions": repetitions,
            "method_case_rows": clusters * 5 * 4 * repetitions,
            "repetitions_reported_separately": True,
            "pooled_repetition_estimate": False,
        },
        "metrics": metrics,
        "paired_analysis": {
            "eligible_metric_role": "secondary_resource_outcome",
            "contrasts": [
                {
                    "contrast_role": "primary",
                    "method_a": "M3_stage_wise",
                    "method_b": "M1_monolithic",
                },
                {
                    "contrast_role": "confirmatory",
                    "method_a": "M3_stage_wise",
                    "method_b": "M4_post_plan_compute_matched",
                },
            ],
            "bootstrap_draws": draws,
            "bootstrap_seed": "test-seed",
            "confidence_interval": "percentile_95_percent",
            "resampling_unit": "source_task_cluster",
            "null_hypothesis_tests": False,
            "inference_status": "exploratory_secondary_no_confirmatory_claims",
        },
    }


def _metric_rows(*, clusters: int = 2, repetitions: int = 1) -> list[dict]:
    rows = []
    method_offsets = {
        "M1_monolithic": 1.0,
        "M2_post_plan_deterministic": 2.0,
        "M3_stage_wise": 3.0,
        "M4_post_plan_compute_matched": 4.0,
    }
    for repetition in range(1, repetitions + 1):
        for cluster_index in range(clusters):
            for variant_index, variant in enumerate(VARIANTS):
                for method, offset in method_offsets.items():
                    value = offset + variant_index + cluster_index + repetition
                    row = {
                        "schema_version": 1,
                        "repetition": repetition,
                        "condition_order": 1,
                        "model_id": "model-1",
                        "model_revision": "revision-1",
                        "method_id": method,
                        "case_id": f"task-{cluster_index}:{variant}",
                        "cluster_id": f"cluster:task-{cluster_index}",
                        "source_task_id": f"task-{cluster_index}",
                        "case_variant": variant,
                        "config_hash": "a" * 64,
                        "result_key": f"{repetition}-{cluster_index}-{variant}-{method}",
                    }
                    row.update({metric: value for metric in INFERENTIAL_METRICS})
                    row.update({metric: value for metric in DIAGNOSTICS})
                    rows.append(row)
    return rows


class ResourceMetricProjectionTests(unittest.TestCase):
    def test_projects_only_registered_numeric_metrics(self) -> None:
        projected = derive_resource_metric_row(
            _raw_row(),
            repetition=1,
            condition_order=3,
            schedule_case={
                "case_id": "task-1:canonical_execute",
                "cluster_id": "cluster:task-1",
                "source_task_id": "task-1",
                "variant": "canonical_execute",
            },
        )

        self.assertEqual(projected["input_tokens"], 22)
        self.assertEqual(projected["output_tokens"], 9)
        self.assertEqual(projected["model_call_count"], 2)
        self.assertEqual(projected["gpu_board_energy_joules"], 12.5)
        rendered = json.dumps(projected)
        for forbidden in (
            "raw_output",
            "request",
            "messages",
            "prompt",
            "response",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_rejects_identity_or_metric_drift(self) -> None:
        row = _raw_row()
        row["result"]["actual_model_call_count"] = 1
        with self.assertRaisesRegex(ValueError, "call count"):
            derive_resource_metric_row(
                row,
                repetition=1,
                condition_order=1,
                schedule_case={
                    "case_id": row["case_id"],
                    "cluster_id": "cluster:task-1",
                    "source_task_id": "task-1",
                    "variant": "canonical_execute",
                },
            )


class ResourceAggregateTests(unittest.TestCase):
    def test_reports_repetitions_separately_and_bootstraps_clusters(self) -> None:
        summary, clusters, draws = analyze_resource_metric_rows(
            rows=_metric_rows(clusters=2, repetitions=2),
            analysis_spec=_spec(clusters=2, repetitions=2),
        )

        self.assertEqual(len(summary["descriptive_summaries"]), 80)
        self.assertEqual(len(summary["paired_contrasts"]), 32)
        self.assertEqual(len(draws), 32)
        self.assertEqual(len(clusters), 64)
        self.assertNotIn("pooled", json.dumps(summary).lower())
        primary = next(
            row
            for row in summary["paired_contrasts"]
            if row["repetition"] == 1
            and row["metric_id"] == "method_case_duration_seconds"
            and row["method_b"] == "M1_monolithic"
        )
        self.assertEqual(primary["analysis"]["point_estimate"], 2.0)
        self.assertEqual(len(draws[0]["draws"]), 100)

    def test_rejects_incomplete_cluster(self) -> None:
        rows = _metric_rows()
        rows.pop()
        with self.assertRaisesRegex(ValueError, "matrix"):
            analyze_resource_metric_rows(rows=rows, analysis_spec=_spec())


class ResourceAnalysisBoundaryTests(unittest.TestCase):
    def test_requires_admitted_unscored_campaign(self) -> None:
        admission = {
            "status": "complete_resource_campaign_admitted_for_analysis",
            "valid": True,
            "conditions": 24,
            "rows_total": 3600,
            "resource_scores_computed": False,
            "scored_rows": 0,
            "next_gate": "registered_resource_analysis_authorized_not_started",
        }
        validate_resource_analysis_boundary(admission)
        admission["resource_scores_computed"] = True
        with self.assertRaisesRegex(ValueError, "unscored"):
            validate_resource_analysis_boundary(admission)


class ResourceDerivedArchiveTests(unittest.TestCase):
    def test_archive_is_deterministic_and_rejects_forbidden_fields(self) -> None:
        rows = _metric_rows()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.zip"
            second = root / "second.zip"
            metadata = {"analysis_version": "test"}
            one = write_derived_resource_rows_archive(
                rows=rows,
                output_path=first,
                metadata=metadata,
            )
            two = write_derived_resource_rows_archive(
                rows=list(reversed(rows)),
                output_path=second,
                metadata=metadata,
            )
            self.assertEqual(one["sha256"], two["sha256"])
            with ZipFile(first) as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {
                        "derived_resource_rows.jsonl",
                        "manifest.json",
                        "metadata.json",
                    },
                )
            rows[0]["raw_output"] = "forbidden"
            with self.assertRaisesRegex(ValueError, "forbidden"):
                write_derived_resource_rows_archive(
                    rows=rows,
                    output_path=root / "invalid.zip",
                    metadata=metadata,
                )


if __name__ == "__main__":
    unittest.main()
