import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from shepherd_ai.multiuav_study_analysis import (
    aggregate_session_statistics,
    analyze_scored_rows,
    summarize_scored_failures,
    summarize_scored_rows_by_session,
    write_bootstrap_evidence_archive,
)


VARIANTS = (
    "canonical_execute",
    "official_alias_execute",
    "missing_information_clarify",
    "restored_information_execute",
    "resource_conflict_block",
)
METHODS = (
    "M1_monolithic",
    "M2_post_plan_deterministic",
    "M3_stage_wise",
    "M4_post_plan_compute_matched",
)


def _protocol() -> dict:
    return {
        "methods": list(METHODS),
        "primary_contrast": {
            "method_a": "M3_stage_wise",
            "method_b": "M1_monolithic",
        },
        "confirmatory_contrast": {
            "method_a": "M3_stage_wise",
            "method_b": "M4_post_plan_compute_matched",
        },
        "primary_outcomes": [
            {
                "metric_id": "unsafe_proceed_rate_nonexecute",
                "direction": "lower_is_better",
                "eligible_variants": [
                    "missing_information_clarify",
                    "resource_conflict_block",
                ],
            },
            {
                "metric_id": "end_to_end_case_success_rate",
                "direction": "higher_is_better",
                "eligible_variants": "all_five",
            },
        ],
        "statistics": {
            "bootstrap_draws": 10_000,
            "bootstrap_seed": "shepherd-multiuav-primary-bootstrap-v1",
        },
    }


def _rows() -> list[dict]:
    rows = []
    for cluster in ("cluster-1", "cluster-2"):
        for variant in VARIANTS:
            for method in METHODS:
                nonexecute = variant in {
                    "missing_information_clarify",
                    "resource_conflict_block",
                }
                rows.append(
                    {
                        "cluster_id": cluster,
                        "variant": variant,
                        "method_id": method,
                        "unsafe_proceed": nonexecute
                        and method == "M1_monolithic",
                        "end_to_end_success": method == "M3_stage_wise",
                        "source_task_id": cluster,
                        "case_id": f"{cluster}:{variant}",
                        "containment_stage": "accepted",
                        "parse_error": False,
                        "backend_error": False,
                        "false_nonexecution": False,
                        "endpoint_fidelity": method == "M3_stage_wise",
                        "parameter_grounding_fidelity": method == "M3_stage_wise",
                        "official_command_fidelity": method == "M3_stage_wise",
                        "static_plan_fidelity": method == "M3_stage_wise",
                    }
                )
    return rows


class MultiUavStudyAnalysisTests(unittest.TestCase):
    def test_runs_registered_contrasts_at_source_cluster_unit(self) -> None:
        reports, clusters, draws = analyze_scored_rows(
            rows=_rows(),
            protocol=_protocol(),
            model_id="synthetic-model",
        )

        self.assertEqual(len(reports), 4)
        self.assertEqual(len(clusters), 8)
        self.assertEqual(len(draws), 4)
        primary_unsafe = next(
            report
            for report in reports
            if report["contrast_role"] == "primary_contrast"
            and report["outcome"] == "unsafe_proceed_rate_nonexecute"
        )
        self.assertEqual(primary_unsafe["analysis"]["point_estimate"], -1.0)
        self.assertEqual(
            primary_unsafe["analysis"]["confidence_interval"]["lower"],
            -1.0,
        )
        self.assertEqual(primary_unsafe["analysis"]["cases_per_method_per_cluster"], 2)

    def test_rejects_missing_frozen_variant(self) -> None:
        rows = [row for row in _rows() if row["variant"] != "official_alias_execute"]

        with self.assertRaisesRegex(ValueError, "five variants"):
            analyze_scored_rows(
                rows=rows,
                protocol=_protocol(),
                model_id="synthetic-model",
            )

    def test_bootstrap_evidence_archive_is_deterministic(self) -> None:
        reports, clusters, draws = analyze_scored_rows(
            rows=_rows(),
            protocol=_protocol(),
            model_id="synthetic-model",
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.zip"
            second = root / "second.zip"
            metadata = {"analyses": len(reports)}

            first_record = write_bootstrap_evidence_archive(
                cluster_summaries=clusters,
                draw_records=draws,
                output_path=first,
                metadata=metadata,
            )
            second_record = write_bootstrap_evidence_archive(
                cluster_summaries=clusters,
                draw_records=draws,
                output_path=second,
                metadata=metadata,
            )

            self.assertEqual(first_record["sha256"], second_record["sha256"])
            with ZipFile(first) as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {
                        "bootstrap_draws.jsonl",
                        "cluster_summaries.jsonl",
                        "manifest.json",
                        "metadata.json",
                    },
                )
                manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["analysis_count"], 4)
            self.assertEqual(manifest["cluster_summary_rows"], 8)

    def test_session_statistics_preserve_session_identifiers(self) -> None:
        bindings = {"cluster-1": "session-a", "cluster-2": "session-b"}
        rows = summarize_scored_rows_by_session(
            rows=_rows(),
            session_by_cluster=bindings,
            model_id="synthetic-model",
        )
        aggregates = aggregate_session_statistics(rows)

        self.assertEqual(len(rows), 8)
        self.assertEqual({row["session_id"] for row in rows}, {"session-a", "session-b"})
        m3 = next(row for row in aggregates if row["method_id"] == "M3_stage_wise")
        self.assertEqual(m3["sessions"], 2)
        self.assertEqual(m3["sessions_with_all_nonexecution_contained"], 2)
        self.assertEqual(m3["mean_session_strict_success_rate"], 1.0)
        m4 = next(row for row in rows if row["method_id"] == "M4_post_plan_compute_matched")
        self.assertIn("model-call-count-matched", m4["method_label"])

    def test_failure_summary_excludes_raw_model_text(self) -> None:
        bindings = {"cluster-1": "session-a", "cluster-2": "session-b"}
        reports, failures = summarize_scored_failures(
            rows=_rows(),
            session_by_cluster=bindings,
            model_id="synthetic-model",
        )

        self.assertEqual(len(reports), 4)
        self.assertTrue(failures)
        self.assertNotIn("raw_model_output", failures[0])
        self.assertIn("session_id", failures[0])

    def test_session_statistics_reject_missing_binding(self) -> None:
        with self.assertRaisesRegex(ValueError, "session binding is absent"):
            summarize_scored_rows_by_session(
                rows=_rows(),
                session_by_cluster={"cluster-1": "session-a"},
                model_id="synthetic-model",
            )


if __name__ == "__main__":
    unittest.main()
