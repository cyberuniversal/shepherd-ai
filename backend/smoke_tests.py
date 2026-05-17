import asyncio
import json
import tempfile

from backend.controller import SwarmManager
from backend.action_script import synthesize_action_script
from backend.assurance import evaluate_runtime_assurance
from backend.assurance_report import generate_assurance_report, write_assurance_report
from backend.brain import MissionParser
from backend.evidence_log import EvidenceLogger
from backend.evidence_replay import EvidenceReplayHarness
from backend.mission_dataset import (
    DEFAULT_ADVERSARIAL_PATH,
    DEFAULT_AUGMENTATION_PATH,
    DEFAULT_BENCHMARK_PATH,
    evaluate_dataset,
    export_training_rows,
    validate_dataset,
    write_json_report,
    write_markdown_report,
)
from backend.learned_parser import (
    BOUNDED_OUTPUT_FIELDS,
    StrictIntentAdapter,
    coerce_bounded_intent,
    load_artifact,
    load_frozen_splits,
    train_baseline_model,
)
from backend.parser_failure_analysis import analyze_report, write_analysis, write_markdown_analysis
from backend.parser_comparison import compare_artifacts, compare_reports, write_comparison, write_markdown_comparison
from backend.parser_promotion import TRANSFORMER_MODEL_CANDIDATE, run_adapter_promotion_gate, run_promotion_gate
from backend.transformer_parser import (
    TRANSFORMER_CORPUS_SCHEMA,
    coerce_generated_text,
    dependency_status,
    load_corpus_records,
    write_training_corpus,
)
from backend.mission_program import compile_mission_program
from backend.safety import ForbiddenZone, validate_mission_program, validate_route_leg
from backend.scenario_fixtures import generate_scenario_records
from backend.scenario_regression import ScenarioRegressionRunner, write_regression_report
from backend.signing import SignatureManager
from backend.signing import digest_payload
from backend.spatial import resolve_relative_target
from hardware_bridge.facade import FacadeCommandRejected, MAVSDKFacade


class FakeAction:
    def __init__(self):
        self.calls = []

    async def arm(self):
        self.calls.append(("arm",))

    async def set_takeoff_altitude(self, altitude):
        self.calls.append(("set_takeoff_altitude", altitude))

    async def takeoff(self):
        self.calls.append(("takeoff",))

    async def goto_location(self, lat, lng, alt, yaw):
        self.calls.append(("goto_location", lat, lng, alt, yaw))

    async def return_to_launch(self):
        self.calls.append(("return_to_launch",))

    async def land(self):
        self.calls.append(("land",))


class FakeSystem:
    def __init__(self):
        self.action = FakeAction()


class FakeBridge:
    def status(self):
        return {
            "mavsdk_available": True,
            "connected_count": 1,
            "connected_drones": [{"drone_id": "alpha-1", "address": "udp://:14540"}],
        }

    async def get_all_telemetry(self):
        return {
            "alpha-1": {
                "telemetry_ok": True,
                "drone_id": "alpha-1",
                "address": "udp://:14540",
                "lat": 24.7201,
                "lng": 46.6812,
                "alt": 17.5,
                "battery_percent": 88.0,
                "flight_mode": "HOLD",
                "updated_at": 123.0,
            }
        }

    async def execute_program(self, program):
        return {
            drone_program["drone_id"]: {
                "executed": True,
                "facade": "MAVSDKFacade",
            }
            for drone_program in program.get("drone_programs", [])
        }


class FakeDisconnectedBridge:
    def status(self):
        return {
            "mavsdk_available": True,
            "connected_count": 0,
            "connected_drones": [],
        }

    async def execute_program(self, program):
        raise AssertionError("preflight should block before bridge execution")


def test_relative_target_resolution():
    target = resolve_relative_target(
        (24.7136, 46.6753),
        330,
        {
            "kafd": (24.7610, 46.6402),
            "masmak": (24.6312, 46.7133),
        },
        direction="front",
        cone_deg=90,
    )
    assert target is not None
    assert target["name"] == "kafd"


def test_geometric_sandbox_blocks_forbidden_polygon():
    zone = ForbiddenZone(
        "test_square",
        [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)],
        "test_zone",
    )
    blocked = validate_route_leg("alpha-1", (0.5, -1.0), (0.5, 2.0), 10.0, forbidden_zones=[zone])
    assert not blocked["passed"]
    clear = validate_route_leg("alpha-1", (24.70, 46.60), (24.71, 46.61), 10.0, forbidden_zones=[zone])
    assert clear["passed"], clear["issues"]


def test_mission_program_safety_passes_normal_riyadh_route():
    swarm = SwarmManager()
    assigned, _ = swarm.allocate_task(24.7610, 46.6402, required_drones=1)
    drones = [swarm.fleet[drone_id] for drone_id in assigned]
    program = compile_mission_program(
        "send one drone to kafd",
        {"action": "scout", "target_zone": "kafd", "pattern": "perimeter"},
        {"lat": 24.7610, "lng": 46.6402},
        drones,
        live_mode=False,
    )
    safety = validate_mission_program(program, {drone.id: (drone.lat, drone.lng) for drone in drones})
    assert safety["passed"], safety["issues"]


def test_shepherd_ir_v2_contract_fields():
    swarm = SwarmManager()
    assigned, _ = swarm.allocate_task(24.7610, 46.6402, required_drones=1)
    drones = [swarm.fleet[drone_id] for drone_id in assigned]
    intent = {
        "action": "scout",
        "target_zone": "kafd",
        "pattern": "perimeter",
        "confidence": 0.83,
        "needs_confirmation": True,
        "parser": "heuristic",
    }
    program = compile_mission_program(
        "send one drone to kafd",
        intent,
        {"lat": 24.7610, "lng": 46.6402},
        drones,
        live_mode=True,
    )

    assert program["language"] == "SHEPHERD-IR/2.0"
    assert program["schema_version"] == "2.0"
    assert program["source"]["modality"] == "text"
    assert program["source"]["utterance_hash"] != "send one drone to kafd"
    assert program["intent_contract"]["confidence"] == 0.83
    assert program["constraints"]["confirmation_required"]
    assert program["constraints"]["live_dispatch_requested"]
    assert "facade_ops_whitelisted" in program["assurance"]["preconditions"]
    assert "link_health_monitor" in program["assurance"]["monitors"]
    assert program["allocation"]["selected_vehicles"] == assigned
    assert program["provenance"]["model_versions"]["intent"] == "heuristic"
    assert program["mission_digest"]
    assert digest_payload(program, recursive_signature_fields=True) == program["mission_digest"]
    assert program["provenance"]["signature"]["algorithm"] == "HMAC-SHA256"
    assert program["provenance"]["signature"]["payload_digest"] == program["mission_digest"]


def test_action_script_has_no_artificial_route_events():
    swarm = SwarmManager()
    assigned, _ = swarm.allocate_task(24.7610, 46.6402, required_drones=1)
    drones = [swarm.fleet[drone_id] for drone_id in assigned]
    program = compile_mission_program(
        "send one drone to kafd",
        {"action": "scout", "target_zone": "kafd", "pattern": "perimeter"},
        {"lat": 24.7610, "lng": 46.6402},
        drones,
        live_mode=False,
    )
    script = synthesize_action_script(program)
    assert script["sensor_events"] == []
    assert script["route_patches"] == []
    assert "ooda_events" not in script
    assert "reroute" not in script["script"].lower()


async def test_live_preflight_blocks_unconnected_drone():
    swarm = SwarmManager()
    swarm.live_mode = True
    swarm.bridge = FakeDisconnectedBridge()
    assigned, _ = swarm.allocate_task(24.7610, 46.6402, required_drones=1, specific_drones=["alpha-1"])
    drones = [swarm.fleet[drone_id] for drone_id in assigned]
    program = compile_mission_program(
        "send alpha-1 to kafd",
        {"action": "scout", "target_zone": "kafd", "pattern": "perimeter"},
        {"lat": 24.7610, "lng": 46.6402},
        drones,
        live_mode=True,
    )

    result = await swarm.execute_mission_program(program)
    assert not result["executed"]
    assert result["reason"] == "preflight_failed"
    assert "alpha-1: no live MAVLink connection" in result["preflight"]["issues"]


async def test_live_preflight_allows_connected_drone():
    swarm = SwarmManager()
    swarm.live_mode = True
    swarm.bridge = FakeBridge()
    swarm.mark_live_connected("alpha-1", "udp://:14540")
    assigned, _ = swarm.allocate_task(24.7610, 46.6402, required_drones=1, specific_drones=["alpha-1"])
    drones = [swarm.fleet[drone_id] for drone_id in assigned]
    program = compile_mission_program(
        "send alpha-1 to kafd",
        {"action": "scout", "target_zone": "kafd", "pattern": "perimeter"},
        {"lat": 24.7610, "lng": 46.6402},
        drones,
        live_mode=True,
    )

    result = await swarm.execute_mission_program(program)
    assert result["executed"]
    assert result["preflight"]["passed"]


def test_runtime_assurance_reports_live_link_without_dispatch():
    swarm = SwarmManager()
    assigned, _ = swarm.allocate_task(24.7610, 46.6402, required_drones=1, specific_drones=["alpha-1"])
    drones = [swarm.fleet[drone_id] for drone_id in assigned]
    program = compile_mission_program(
        "send alpha-1 to kafd",
        {"action": "scout", "target_zone": "kafd", "pattern": "perimeter"},
        {"lat": 24.7610, "lng": 46.6402},
        drones,
        live_mode=True,
    )

    assurance = evaluate_runtime_assurance(
        {
            "assigned": assigned,
            "mission_programs": [program],
            "safety_reports": [{"passed": True, "issues": []}],
        },
        swarm.get_fleet_state(),
    )

    assert assurance["summary"]["report_only"]
    assert assurance["summary"]["critical_count"] == 1
    assert assurance["events"][0]["monitor"] == "link_health"
    assert assurance["events"][0]["report_only"]
    assert swarm.fleet["alpha-1"].live_connected is False


def test_mission_command_dataset_seed_validates():
    result = validate_dataset()
    assert result["valid"], result["errors"]
    assert result["summary"]["total"] >= 30
    assert result["summary"]["language_counts"]["en"] >= 15
    assert result["summary"]["language_counts"]["ar"] >= 15
    assert result["summary"]["split_counts"]["train"] >= 20
    assert result["summary"]["split_counts"]["eval"] >= 6
    assert result["summary"]["split_counts"]["holdout"] >= 4

    rows = export_training_rows()
    assert rows
    assert all("input" in row and "target_json" in row and "split" in row for row in rows)

    evaluation = asyncio.run(evaluate_dataset())
    assert evaluation["valid"], evaluation["errors"]
    assert evaluation["summary"]["evaluated"] == result["summary"]["total"]
    metrics = evaluation["summary"]["field_metrics"]
    assert metrics["action"]["accuracy"] >= 0.95
    assert metrics["drone_count"]["accuracy"] >= 0.9
    assert metrics["target_zone"]["accuracy"] >= 0.9
    assert metrics["pattern"]["accuracy"] >= 0.9
    assert evaluation["summary"]["subset_matches"] >= 30
    assert "language_metrics" in evaluation["summary"]
    assert "action_confusion" in evaluation["summary"]

    benchmark = validate_dataset(DEFAULT_BENCHMARK_PATH)
    assert benchmark["valid"], benchmark["errors"]
    assert benchmark["summary"]["total"] >= 200
    assert benchmark["summary"]["language_counts"]["en"] >= 100
    assert benchmark["summary"]["language_counts"]["ar"] >= 90

    benchmark_evaluation = asyncio.run(evaluate_dataset(DEFAULT_BENCHMARK_PATH))
    assert benchmark_evaluation["valid"], benchmark_evaluation["errors"]
    assert benchmark_evaluation["summary"]["evaluated"] == benchmark["summary"]["total"]
    assert benchmark_evaluation["summary"]["field_metrics"]["target_zone"]["accuracy"] >= 0.9

    adversarial = validate_dataset(DEFAULT_ADVERSARIAL_PATH)
    assert adversarial["valid"], adversarial["errors"]
    assert adversarial["summary"]["total"] >= 60
    assert adversarial["summary"]["language_counts"]["en"] >= 30
    assert adversarial["summary"]["language_counts"]["ar"] >= 30
    assert adversarial["summary"]["split_counts"]["holdout"] >= 60

    augmentation = validate_dataset(DEFAULT_AUGMENTATION_PATH)
    assert augmentation["valid"], augmentation["errors"]
    assert augmentation["summary"]["total"] >= 48
    assert augmentation["summary"]["language_counts"]["en"] >= 24
    assert augmentation["summary"]["language_counts"]["ar"] >= 24
    assert augmentation["summary"]["split_counts"]["train"] == augmentation["summary"]["total"]
    assert augmentation["summary"]["split_counts"]["eval"] == 0
    assert augmentation["summary"]["split_counts"]["holdout"] == 0

    adversarial_evaluation = asyncio.run(evaluate_dataset(DEFAULT_ADVERSARIAL_PATH))
    assert adversarial_evaluation["valid"], adversarial_evaluation["errors"]
    assert adversarial_evaluation["summary"]["evaluated"] == adversarial["summary"]["total"]
    assert "language_metrics" in adversarial_evaluation["summary"]
    assert "action_confusion" in adversarial_evaluation["summary"]
    assert "failed_example_count" in adversarial_evaluation["summary"]

    with tempfile.TemporaryDirectory() as tmpdir:
        json_report = write_json_report(benchmark_evaluation, f"{tmpdir}/parser-report.json")
        markdown_report = write_markdown_report(benchmark_evaluation, f"{tmpdir}/parser-report.md")
        adversarial_json = write_json_report(adversarial_evaluation, f"{tmpdir}/adversarial-parser-report.json")
        adversarial_markdown = write_markdown_report(
            adversarial_evaluation,
            f"{tmpdir}/adversarial-parser-report.md",
        )
        assert json_report.endswith(".json")
        assert markdown_report.endswith(".md")
        assert adversarial_json.endswith(".json")
        assert adversarial_markdown.endswith(".md")


def test_learned_parser_baseline_scaffold_keeps_frozen_splits():
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_path = f"{tmpdir}/learned-parser-baseline.json"
        report_path = f"{tmpdir}/learned-parser-report.json"
        result = train_baseline_model(artifact_path=artifact_path, report_path=report_path)

        artifact = result["artifact"]
        report = result["report"]
        train_ids = set(artifact["dataset"]["train_ids"])
        adversarial_ids = set(artifact["dataset"]["adversarial_ids"])
        assert artifact["schema"] == "shepherd-learned-parser-baseline/1.0"
        assert artifact["contract"]["output"] == "bounded_intent_json_only"
        assert artifact["contract"]["dispatch_authority"] is False
        assert len(train_ids) >= 100
        assert len(adversarial_ids) >= 60
        assert train_ids.isdisjoint(adversarial_ids)
        assert report["summary"]["adversarial_used_for_training"] is False
        assert report["summary"]["train_count"] == len(train_ids)
        assert report["summary"]["adversarial_count"] == len(adversarial_ids)
        assert report["split_reports"]["eval"]["bounded_output_count"] == report["split_reports"]["eval"]["total"]
        assert report["split_reports"]["adversarial"]["bounded_output_count"] == report["split_reports"]["adversarial"]["total"]

        loaded = load_artifact(artifact_path)
        adapter = StrictIntentAdapter(loaded)
        prediction = adapter.predict("Send two drones to KAFD")
        assert set(prediction).issubset(BOUNDED_OUTPUT_FIELDS)
        assert prediction["parser"] == "learned_baseline"
        assert prediction["needs_confirmation"] is True
        assert prediction["model_digest"] == loaded["artifact_digest"]
        assert "dispatch" not in prediction


def test_targeted_augmentation_stays_train_only():
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_path = f"{tmpdir}/learned-parser-augmented.json"
        report_path = f"{tmpdir}/learned-parser-augmented-report.json"
        result = train_baseline_model(
            augmentation_path=DEFAULT_AUGMENTATION_PATH,
            artifact_path=artifact_path,
            report_path=report_path,
        )

        artifact = result["artifact"]
        report = result["report"]
        train_ids = set(artifact["dataset"]["train_ids"])
        augmentation_ids = set(artifact["dataset"]["augmentation_ids"])
        adversarial_ids = set(artifact["dataset"]["adversarial_ids"])
        assert artifact["dataset"]["augmentation_path"] == str(DEFAULT_AUGMENTATION_PATH)
        assert len(augmentation_ids) >= 48
        assert augmentation_ids.issubset(train_ids)
        assert train_ids.isdisjoint(adversarial_ids)
        assert report["summary"]["augmentation_count"] == len(augmentation_ids)
        assert report["summary"]["adversarial_used_for_training"] is False
        assert report["split_reports"]["augmentation"]["total"] == len(augmentation_ids)
        assert report["split_reports"]["adversarial"]["total"] == len(adversarial_ids)


def test_parser_promotion_gate_blocks_weak_candidate():
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_path = f"{tmpdir}/learned-parser-baseline.json"
        report_path = f"{tmpdir}/learned-parser-report.json"
        promotion_path = f"{tmpdir}/promotion-gate.json"
        train_baseline_model(artifact_path=artifact_path, report_path=report_path)

        report = run_promotion_gate(artifact_path, report_path=promotion_path)
        assert not report["promoted"]
        assert report["contract_checks"]["passed"]
        assert report["summary"]["adversarial_used_for_training"] is False
        assert report["split_checks"]["eval"]["passed"] is False
        assert report["split_checks"]["holdout"]["passed"] is False
        assert report["split_checks"]["adversarial"]["passed"] is False
        assert any(failure["scope"] == "adversarial" for failure in report["failures"])

        permissive = {
            "eval": {"subset_accuracy": 0.0, "bounded_output_rate": 1.0, "field_metrics": {}},
            "holdout": {"subset_accuracy": 0.0, "bounded_output_rate": 1.0, "field_metrics": {}},
            "adversarial": {"subset_accuracy": 0.0, "bounded_output_rate": 1.0, "field_metrics": {}},
        }
        permissive_report = run_promotion_gate(
            artifact_path,
            thresholds=permissive,
            report_path=f"{tmpdir}/permissive-promotion-gate.json",
        )
        assert permissive_report["promoted"]


def test_parser_failure_analysis_reports_grouped_failures():
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_path = f"{tmpdir}/learned-parser-baseline.json"
        report_path = f"{tmpdir}/learned-parser-report.json"
        result = train_baseline_model(artifact_path=artifact_path, report_path=report_path)

        analysis = analyze_report(result["report"])
        assert analysis["schema"] == "shepherd-parser-failure-analysis/1.0"
        assert analysis["summary"]["total_examples"] >= 200
        assert analysis["summary"]["failed_examples"] > 0
        assert analysis["summary"]["field_failure_counts"]["target_zone"] > 0
        assert "eval" in analysis["by_split"]
        assert "adversarial" in analysis["by_split"]
        assert "en" in analysis["by_language"]
        assert "ar" in analysis["by_language"]
        assert "target_zone" in analysis["field_details"]
        assert analysis["field_details"]["target_zone"]["top_confusions"]
        assert analysis["highest_risk_examples"]
        assert any(example["command"] for example in analysis["highest_risk_examples"])
        assert analysis["recommendations"]

        json_path = write_analysis(analysis, f"{tmpdir}/failure-analysis.json")
        markdown_path = write_markdown_analysis(analysis, f"{tmpdir}/failure-analysis.md")
        assert json_path.endswith(".json")
        assert markdown_path.endswith(".md")


def test_parser_comparison_reports_augmented_delta():
    with tempfile.TemporaryDirectory() as tmpdir:
        baseline = train_baseline_model(
            artifact_path=f"{tmpdir}/learned-parser-baseline.json",
            report_path=f"{tmpdir}/learned-parser-report.json",
        )
        augmented = train_baseline_model(
            augmentation_path=DEFAULT_AUGMENTATION_PATH,
            artifact_path=f"{tmpdir}/learned-parser-augmented.json",
            report_path=f"{tmpdir}/learned-parser-augmented-report.json",
        )

        comparison = compare_reports(baseline["report"], augmented["report"])
        assert comparison["schema"] == "shepherd-parser-comparison/1.0"
        assert comparison["scope"]["splits"] == ["eval", "holdout", "adversarial"]
        assert comparison["summary"]["compared_examples"] >= 120
        assert comparison["sources"]["candidate"]["summary"]["augmentation_count"] >= 48
        assert comparison["sources"]["candidate"]["summary"]["adversarial_used_for_training"] is False
        assert "augmentation" not in comparison["split_deltas"]
        assert "target_zone" in comparison["field_deltas"]
        assert comparison["recommendations"]

        artifact_comparison = compare_artifacts(
            f"{tmpdir}/learned-parser-baseline.json",
            f"{tmpdir}/learned-parser-augmented.json",
        )
        assert artifact_comparison["sources"]["candidate"]["artifact_training"]["augmentation_count"] >= 48
        assert artifact_comparison["sources"]["candidate"]["artifact_training"]["adversarial_used_for_training"] is False

        json_path = write_comparison(comparison, f"{tmpdir}/parser-comparison.json")
        markdown_path = write_markdown_comparison(comparison, f"{tmpdir}/parser-comparison.md")
        assert json_path.endswith(".json")
        assert markdown_path.endswith(".md")


def test_parser_promotion_gate_accepts_transformer_adapter_candidate():
    class PerfectTransformerAdapter:
        def __init__(self, examples, model_id, model_digest):
            self.model_id = model_id
            self.model_digest = model_digest
            self.expected_by_command = {
                example["command"]: example["expected_intent"]
                for example in examples
            }

        def predict(self, command):
            return coerce_bounded_intent(
                self.expected_by_command[command],
                confidence=0.99,
                model_id=self.model_id,
                model_digest=self.model_digest,
            )

    with tempfile.TemporaryDirectory() as tmpdir:
        splits = load_frozen_splits()
        all_examples = [example for rows in splits.values() for example in rows]
        model_id = "test-transformer-adapter"
        model_digest = "test-transformer-digest"
        metadata = {
            "candidate_type": TRANSFORMER_MODEL_CANDIDATE,
            "candidate_path": f"{tmpdir}/model",
            "model_id": model_id,
            "artifact_digest": model_digest,
            "contract": {
                "output": "bounded_intent_json_only",
                "dispatch_authority": False,
                "confirmation_required": True,
                "deterministic_backend_required": True,
            },
            "dataset": {
                "train_ids": [example["id"] for example in splits["train"]],
                "eval_ids": [example["id"] for example in splits["eval"]],
                "holdout_ids": [example["id"] for example in splits["holdout"]],
                "adversarial_ids": [example["id"] for example in splits["adversarial"]],
            },
        }
        report = run_adapter_promotion_gate(
            PerfectTransformerAdapter(all_examples, model_id, model_digest),
            metadata,
            splits,
            report_path=f"{tmpdir}/transformer-promotion-gate.json",
        )
        assert report["promoted"]
        assert report["candidate_type"] == TRANSFORMER_MODEL_CANDIDATE
        assert report["contract_checks"]["passed"]
        assert report["summary"]["adversarial_used_for_training"] is False
        assert report["split_checks"]["eval"]["passed"]
        assert report["split_checks"]["holdout"]["passed"]
        assert report["split_checks"]["adversarial"]["passed"]


def test_transformer_parser_scaffold_prepares_frozen_corpus():
    with tempfile.TemporaryDirectory() as tmpdir:
        base_result = write_training_corpus(f"{tmpdir}/base")
        base_manifest = base_result["manifest"]
        base_train_count = base_manifest["splits"]["train"]["count"]

        result = write_training_corpus(f"{tmpdir}/augmented", augmentation_path=DEFAULT_AUGMENTATION_PATH)
        manifest = result["manifest"]
        assert manifest["schema"] == TRANSFORMER_CORPUS_SCHEMA
        assert manifest["contract"]["dispatch_authority"] is False
        assert manifest["contract"]["confirmation_required"] is True
        assert manifest["dataset"]["augmentation_path"] == str(DEFAULT_AUGMENTATION_PATH)
        assert manifest["splits"]["train"]["count"] >= base_train_count + 48
        assert manifest["splits"]["augmentation"]["count"] >= 48
        assert manifest["splits"]["eval"]["count"] >= 40
        assert manifest["splits"]["holdout"]["count"] >= 20
        assert manifest["splits"]["adversarial"]["count"] >= 60
        assert manifest["splits"]["train"]["used_for_training"] is True
        assert manifest["splits"]["augmentation"]["used_for_training"] is True
        assert manifest["splits"]["adversarial"]["used_for_training"] is False
        assert set(manifest["splits"]["train"]["source_ids"]).isdisjoint(
            set(manifest["splits"]["adversarial"]["source_ids"])
        )

        train_rows = load_corpus_records(manifest["files"]["train"])
        augmentation_rows = load_corpus_records(manifest["files"]["augmentation"])
        adversarial_rows = load_corpus_records(manifest["files"]["adversarial"])
        assert len(train_rows) == manifest["splits"]["train"]["count"]
        assert len(augmentation_rows) == manifest["splits"]["augmentation"]["count"]
        assert {row["id"] for row in augmentation_rows}.issubset({row["id"] for row in train_rows})
        assert len(adversarial_rows) == manifest["splits"]["adversarial"]["count"]
        target = json.loads(train_rows[0]["target_json"])
        assert "intent" in target
        assert "constraints" in target
        assert target["constraints"]["confirmation_required"] is True

    deps = dependency_status()
    assert "ready" in deps
    assert "torch" in deps["packages"]
    assert "transformers" in deps["packages"]

    bounded = coerce_generated_text(
        '{"intent":{"action":"scout","target_zone":"kafd","drone_count":2,"pattern":"perimeter"}}',
        model_id="test-transformer",
        model_digest="digest",
    )
    assert set(bounded).issubset(BOUNDED_OUTPUT_FIELDS)
    assert bounded["needs_confirmation"] is True
    assert bounded["model_id"] == "test-transformer"
    assert bounded["target_zone"] == "kafd"
    assert "dispatch" not in bounded


def test_scenario_fixture_generator_creates_manifest_and_records():
    with tempfile.TemporaryDirectory() as tmpdir:
        signer = SignatureManager(key="scenario-fixture-test-key")
        result = generate_scenario_records(tmpdir, signer=signer)
        assert result["scenario_count"] == 8
        manifest_path = result["manifest_path"]
        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        assert manifest["scenario_count"] == 8
        assert {scenario["scenario_id"] for scenario in manifest["scenarios"]} >= {
            "nominal_kafd_scout",
            "tampered_evidence_record",
            "bad_altitude_envelope",
        }
        for scenario in manifest["scenarios"]:
            assert scenario["evidence_id"].startswith("evidence-")
            assert scenario["expected_pass"] in (True, False)

        logger = EvidenceLogger(tmpdir, signer=signer)
        manifest_regression = ScenarioRegressionRunner(logger).run(manifest_path=manifest_path)
        assert manifest_regression["passed"], manifest_regression["summary"]
        assert manifest_regression["summary"]["total"] == 8
        assert manifest_regression["summary"]["expected_failures"] >= 3
        assert manifest_regression["summary"]["unexpected_failures"] == 0
        assert all(case["expectation_met"] for case in manifest_regression["cases"])

        report_path = write_regression_report(manifest_regression, f"{tmpdir}/regression-report.json")
        with open(report_path, "r", encoding="utf-8") as handle:
            report = json.load(handle)
        assert report["passed"]
        assert report["manifest"]["scenario_count"] == 8

        assurance_report = generate_assurance_report(evidence_logger=logger)
        assert assurance_report["report_only"]
        assert not assurance_report["validation_scope"]["automatic_fallback_enabled"]
        assert not assurance_report["validation_scope"]["dispatch_side_effects"]
        assert assurance_report["summary"]["total_records"] == 8
        assert assurance_report["summary"]["assurance_event_count"] >= 7
        assert assurance_report["summary"]["monitor_counts"]["battery_reserve"] >= 1
        assert assurance_report["summary"]["monitor_counts"]["link_health"] >= 1
        assert assurance_report["summary"]["monitor_counts"]["selected_vehicle_consistency"] >= 1
        assurance_path = write_assurance_report(assurance_report, f"{tmpdir}/assurance-report.json")
        with open(assurance_path, "r", encoding="utf-8") as handle:
            persisted_assurance = json.load(handle)
        assert persisted_assurance["summary"]["total_records"] == 8

        plain_regression = ScenarioRegressionRunner(logger).run()
        assert not plain_regression["passed"]
        assert plain_regression["summary"]["failed"] >= 3


async def test_facade_allows_only_safe_ops():
    system = FakeSystem()
    facade = MAVSDKFacade({"alpha-1": system})
    result = await facade.execute_steps(
        "alpha-1",
        [
            {"op": "ARM"},
            {"op": "TAKEOFF", "altitude_m": 10},
            {"op": "GOTO", "lat": 24.7610, "lng": 46.6402, "altitude_m": 10},
            {"op": "RTL"},
        ],
    )
    assert result["executed"]

    try:
        await facade.execute_steps("alpha-1", [{"op": "KILL"}])
    except FacadeCommandRejected:
        return
    raise AssertionError("KILL operation should be rejected by facade")


async def test_live_telemetry_sync_updates_digital_twin():
    swarm = SwarmManager()
    swarm.live_mode = True
    swarm.bridge = FakeBridge()
    swarm.mark_live_connected("alpha-1", "udp://:14540")
    swarm.fleet["alpha-1"].status = "assigned"
    swarm.fleet["alpha-1"].target = (24.9000, 46.9000)

    result = await swarm.sync_live_telemetry()
    drone = swarm.fleet["alpha-1"]
    assert result["synced"]
    assert drone.live_connected
    assert drone.lat == 24.7201
    assert drone.lng == 46.6812
    assert drone.altitude_m == 17.5
    assert drone.battery == 88.0
    assert drone.nav_state.position_source == "mavsdk_telemetry"

    swarm.step_simulation()
    assert drone.lat == 24.7201
    assert drone.lng == 46.6812


async def test_operator_reference_command_parse():
    parser = MissionParser()
    parser._ollama_available = False
    intent = await parser.parse_intent("Bring two drones to me")
    assert intent["drone_count"] == 2
    assert intent["target_reference"] == "operator"
    assert intent["target_zone"] == "operator_current_position"
    assert intent["action"] == "rendezvous"

    al_nada_intent = await parser.parse_intent("Bring two drones to Al Nada")
    assert al_nada_intent["drone_count"] == 2
    assert al_nada_intent["target_zone"] == "al nada"


async def test_mission_plan_preview_does_not_move_real_swarm():
    from backend import main as backend_main

    backend_main.parser._ollama_available = False
    backend_main.PENDING_MISSION_PLANS.clear()
    real_statuses = {drone_id: drone.status for drone_id, drone in backend_main.swarm.fleet.items()}

    response = await backend_main.create_mission_plan(
        backend_main.CommandInput(command="Send two drones to Al Nada", selected_drones=[])
    )

    assert response["plan_id"] in backend_main.PENDING_MISSION_PLANS
    assert response["status"] == "pending_confirmation"
    assert response["plan_summary"]["confirmable"]
    assert response["execution_results"][0]["mode"] == "pending_confirmation"
    assert {drone_id: drone.status for drone_id, drone in backend_main.swarm.fleet.items()} == real_statuses

    cancelled = await backend_main.cancel_mission_plan(backend_main.MissionPlanRef(plan_id=response["plan_id"]))
    assert cancelled["cancelled"]


async def test_confirmed_mission_writes_evidence_log():
    from backend import main as backend_main

    old_swarm = backend_main.swarm
    old_logger = backend_main.evidence_logger
    backend_main.parser._ollama_available = False
    backend_main.PENDING_MISSION_PLANS.clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            backend_main.swarm = SwarmManager()
            backend_main.evidence_logger = EvidenceLogger(tmpdir)

            plan = await backend_main.create_mission_plan(
                backend_main.CommandInput(command="Send one drone to Al Nada", selected_drones=[])
            )
            assert backend_main.evidence_logger.list_records() == []

            response = await backend_main.confirm_mission_plan(
                backend_main.MissionPlanRef(plan_id=plan["plan_id"])
            )

            evidence = response["evidence"]
            assert evidence["recorded"]
            assert evidence["evidence_id"].startswith("evidence-")
            assert evidence["mission_digests"]
            assert evidence["record_signature"]["algorithm"] == "HMAC-SHA256"

            record = backend_main.evidence_logger.read_record(evidence["evidence_id"])
            assert record["record_type"] == "confirmed_mission"
            assert record["plan_id"] == plan["plan_id"]
            assert record["confirmation"]["confirmed"]
            assert "operator_state" in record["confirmation"]
            assert record["fleet_snapshot_at_confirmation"]["drones"]
            assert record["selected_drones"] == response["assigned"]
            assert record["parser_summary"]["fallback_used"]
            assert record["mission_programs"][0]["language"] == "SHEPHERD-IR/2.0"
            assert record["mission_programs"][0]["mission_digest"] == record["mission_digests"][0]
            assert record["safety_reports"]
            assert "assurance_events" in record
            assert record["assurance_summary"]["report_only"]
            assert record["execution_results"]
            assert record["record_signature"]["payload_digest"] == record["evidence_digest"]
            assert record["verification"]["digest_valid"]
            assert record["verification"]["signature_valid"]

            verify_result = await backend_main.verify_evidence_record(evidence["evidence_id"])
            assert verify_result["digest_valid"]
            assert verify_result["signature_valid"]

            replay_result = await backend_main.replay_evidence_record(evidence["evidence_id"])
            assert replay_result["status"] == "verified"
            assert replay_result["summary"]["verified"]
            assert replay_result["summary"]["replayed_safety_passed"]
            assert replay_result["record_consistency"]["selected_drones_match_programs"]

            direct_replay = EvidenceReplayHarness(backend_main.evidence_logger).replay_record(record)
            assert direct_replay["summary"]["mission_digests_ok"]

            tampered = dict(record)
            tampered["command"] = "tampered command"
            tampered.pop("verification", None)
            tamper_check = backend_main.evidence_logger.verify_record(tampered)
            assert not tamper_check["digest_valid"]
            assert tamper_check["signature_valid"]

            listed = backend_main.evidence_logger.list_records()
            assert listed[0]["evidence_id"] == evidence["evidence_id"]
            assert listed[0]["verified"]

            regression = ScenarioRegressionRunner(backend_main.evidence_logger).run()
            assert regression["passed"]
            assert regression["summary"]["total"] == 1
            assert regression["cases"][0]["status"] == "passed"

            api_regression = await backend_main.run_research_scenario_regression()
            assert api_regression["passed"]
            assert api_regression["summary"]["passed"] == 1

            evidence_path = backend_main.evidence_logger._record_path(evidence["evidence_id"])
            tampered_record = dict(record)
            tampered_record.pop("verification", None)
            tampered_record["command"] = "tampered command from regression test"
            with evidence_path.open("w", encoding="utf-8") as handle:
                json.dump(tampered_record, handle, indent=2, sort_keys=True)
                handle.write("\n")

            failed_regression = ScenarioRegressionRunner(backend_main.evidence_logger).run()
            assert not failed_regression["passed"]
            assert failed_regression["summary"]["failed"] == 1
            assert "evidence_integrity_failed" in failed_regression["cases"][0]["failure_reasons"]
        finally:
            backend_main.swarm = old_swarm
            backend_main.evidence_logger = old_logger
            backend_main.PENDING_MISSION_PLANS.clear()


def main():
    test_relative_target_resolution()
    test_geometric_sandbox_blocks_forbidden_polygon()
    test_mission_program_safety_passes_normal_riyadh_route()
    test_shepherd_ir_v2_contract_fields()
    test_action_script_has_no_artificial_route_events()
    asyncio.run(test_live_preflight_blocks_unconnected_drone())
    asyncio.run(test_live_preflight_allows_connected_drone())
    test_runtime_assurance_reports_live_link_without_dispatch()
    test_mission_command_dataset_seed_validates()
    test_learned_parser_baseline_scaffold_keeps_frozen_splits()
    test_targeted_augmentation_stays_train_only()
    test_parser_promotion_gate_blocks_weak_candidate()
    test_parser_failure_analysis_reports_grouped_failures()
    test_parser_comparison_reports_augmented_delta()
    test_parser_promotion_gate_accepts_transformer_adapter_candidate()
    test_transformer_parser_scaffold_prepares_frozen_corpus()
    test_scenario_fixture_generator_creates_manifest_and_records()
    asyncio.run(test_facade_allows_only_safe_ops())
    asyncio.run(test_live_telemetry_sync_updates_digital_twin())
    asyncio.run(test_operator_reference_command_parse())
    asyncio.run(test_mission_plan_preview_does_not_move_real_swarm())
    asyncio.run(test_confirmed_mission_writes_evidence_log())
    print("backend smoke tests passed")


if __name__ == "__main__":
    main()
