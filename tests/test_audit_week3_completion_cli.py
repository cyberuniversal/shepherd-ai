import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_week3_completion.py"


class AuditWeek3CompletionCliTests(unittest.TestCase):
    def test_cli_writes_completion_gate_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            map_validation = root / "map.json"
            region_validation = root / "region.json"
            evaluation = root / "eval.json"
            dataset_validation = root / "dataset_validation.json"
            coverage = root / "coverage.json"
            status = root / "status.json"
            deferrals = root / "deferrals.json"
            output_json = root / "completion.json"
            output_markdown = root / "completion.md"

            map_validation.write_text(
                json.dumps({"records": 1, "restricted_records": [{}], "obstacle_records": [{}]}),
                encoding="utf-8",
            )
            region_validation.write_text(json.dumps({"geometry_counts": {"polygon": 1}}), encoding="utf-8")
            evaluation.write_text(
                json.dumps(
                    {
                        "summary": {
                            "records": 1,
                            "exact_record_matches": 1,
                            "exact_record_accuracy": 1.0,
                            "reference_matches": 2,
                            "total_references": 2,
                            "reference_accuracy": 1.0,
                        }
                    }
                ),
                encoding="utf-8",
            )
            dataset_validation.write_text(
                json.dumps(
                    {
                        "records": 1,
                        "ambiguous_reference_count": 1,
                        "unresolved_reference_count": 1,
                        "data_type_counts": {"synthetic_grounding_example": 1},
                    }
                ),
                encoding="utf-8",
            )
            coverage.write_text(json.dumps({"map_records": 1, "covered_location_ids": ["loc"], "warnings": []}), encoding="utf-8")
            status.write_text(
                json.dumps(
                    {
                        "readiness": {
                            "development_handoff_ready": True,
                            "reason": "synthetic_grounding_slice_has_validation_evaluation_clarification_and_resolution_artifacts",
                        }
                    }
                ),
                encoding="utf-8",
            )
            deferrals.write_text(
                json.dumps(
                    {
                        "scope": "week3_research_deferrals_v1",
                        "deferrals": {
                            "real_map_or_public_benchmark_provenance_exists": {
                                "status": "deferred_for_week3",
                                "reason": "custom simulation map is sufficient for the synthetic Week 3 gate",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--map-validation",
                    str(map_validation),
                    "--region-map-validation",
                    str(region_validation),
                    "--grounding-evaluation",
                    str(evaluation),
                    "--grounding-dataset-validation",
                    str(dataset_validation),
                    "--coverage-report",
                    str(coverage),
                    "--week3-status",
                    str(status),
                    "--research-deferrals",
                    str(deferrals),
                    "--json-output",
                    str(output_json),
                    "--markdown-output",
                    str(output_markdown),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output_json.read_text(encoding="utf-8"))
            markdown = output_markdown.read_text(encoding="utf-8")

        self.assertIn("advancement_allowed", completed.stdout)
        self.assertFalse(payload["advancement_allowed"])
        self.assertTrue(payload["roadmap_gates_passed"])
        self.assertNotIn("real_map_or_public_benchmark_provenance_exists", payload["blockers"])
        self.assertIn("Research Gates", markdown)

    def test_cli_accepts_human_grounding_benchmark_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            map_validation = root / "map.json"
            region_validation = root / "region.json"
            evaluation = root / "eval.json"
            dataset_validation = root / "dataset_validation.json"
            coverage = root / "coverage.json"
            status = root / "status.json"
            deferrals = root / "deferrals.json"
            human_validation = root / "human_validation.json"
            human_evaluation = root / "human_eval.json"
            output_json = root / "completion.json"
            output_markdown = root / "completion.md"

            map_validation.write_text(
                json.dumps({"records": 1, "restricted_records": [{}], "obstacle_records": [{}]}),
                encoding="utf-8",
            )
            region_validation.write_text(json.dumps({"geometry_counts": {"polygon": 1}}), encoding="utf-8")
            evaluation.write_text(
                json.dumps(
                    {
                        "summary": {
                            "records": 1,
                            "exact_record_matches": 1,
                            "exact_record_accuracy": 1.0,
                            "reference_matches": 2,
                            "total_references": 2,
                            "reference_accuracy": 1.0,
                        }
                    }
                ),
                encoding="utf-8",
            )
            dataset_validation.write_text(
                json.dumps(
                    {
                        "records": 1,
                        "ambiguous_reference_count": 1,
                        "unresolved_reference_count": 1,
                        "data_type_counts": {"synthetic_grounding_example": 1},
                    }
                ),
                encoding="utf-8",
            )
            coverage.write_text(json.dumps({"map_records": 1, "covered_location_ids": ["loc"], "warnings": []}), encoding="utf-8")
            status.write_text(
                json.dumps(
                    {
                        "readiness": {
                            "development_handoff_ready": True,
                            "reason": "synthetic_grounding_slice_has_validation_evaluation_clarification_and_resolution_artifacts",
                        }
                    }
                ),
                encoding="utf-8",
            )
            deferrals.write_text(
                json.dumps(
                    {
                        "scope": "week3_research_deferrals_v1",
                        "deferrals": {
                            "real_map_or_public_benchmark_provenance_exists": {
                                "status": "deferred_for_week3",
                                "reason": "custom simulation map is sufficient for the synthetic Week 3 gate",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            human_validation.write_text(
                json.dumps({"records": 2, "data_type_counts": {"human_written_grounding_benchmark": 2}}),
                encoding="utf-8",
            )
            human_evaluation.write_text(
                json.dumps(
                    {
                        "summary": {
                            "records": 2,
                            "exact_record_matches": 2,
                            "reference_matches": 4,
                            "total_references": 4,
                        }
                    }
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--map-validation",
                    str(map_validation),
                    "--region-map-validation",
                    str(region_validation),
                    "--grounding-evaluation",
                    str(evaluation),
                    "--grounding-dataset-validation",
                    str(dataset_validation),
                    "--coverage-report",
                    str(coverage),
                    "--week3-status",
                    str(status),
                    "--research-deferrals",
                    str(deferrals),
                    "--human-grounding-dataset-validation",
                    str(human_validation),
                    "--human-grounding-evaluation",
                    str(human_evaluation),
                    "--json-output",
                    str(output_json),
                    "--markdown-output",
                    str(output_markdown),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output_json.read_text(encoding="utf-8"))

        self.assertTrue(payload["advancement_allowed"])
        self.assertNotIn("human_collected_grounding_benchmark_exists", payload["blockers"])


if __name__ == "__main__":
    unittest.main()
