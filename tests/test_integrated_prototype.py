import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations  # noqa: E402
from shepherd_ai.integrated_prototype import run_integrated_prototype  # noqa: E402
from shepherd_ai.intent_training import load_intent_model  # noqa: E402
from shepherd_ai.safety import load_safety_policy  # noqa: E402
from shepherd_ai.whisper_asr import load_whisper_predictions  # noqa: E402


MAP_PATH = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
FLEET_PATH = ROOT / "datasets" / "drones" / "week5_three_drone_fleet_v1.json"
POLICY_PATH = ROOT / "datasets" / "safety" / "week7_safety_policy_v1.json"
MODEL_PATH = ROOT / "outputs" / "model_artifacts" / "intent_nb_human_curated_v2.json"
WHISPER_PATH = ROOT / "outputs" / "evaluations" / "whisper_base_audio_predictions_local_gtx1650.jsonl"
VISION_PATH = ROOT / "outputs" / "evaluations" / "week6_visdrone_yolov8n_seed17_e50_completed_summary.json"


def _inputs():
    return {
        "locations": load_map_locations(MAP_PATH),
        "fleet_payload": json.loads(FLEET_PATH.read_text(encoding="utf-8")),
        "safety_policy": load_safety_policy(POLICY_PATH),
        "trained_intent_model": load_intent_model(MODEL_PATH),
        "vision_artifact": {
            "artifact_path": str(VISION_PATH.relative_to(ROOT)),
            "payload": json.loads(VISION_PATH.read_text(encoding="utf-8")),
            "scope": "week6_development_result_not_mission_specific",
        },
    }


class IntegratedPrototypeTests(unittest.TestCase):
    def test_typed_command_uses_trained_intent_interface_and_starts_supervisor(self) -> None:
        result = run_integrated_prototype(
            {"input_type": "typed", "text": "Inspect the greenhouse."},
            intent_system="trained_naive_bayes",
            **_inputs(),
        )

        self.assertEqual(result["status"], "active")
        self.assertEqual(result["intent"]["parser"], "trained_nb_human_curated_v2")
        self.assertEqual(result["supervision"]["mission_status"], "active")
        self.assertEqual(result["vision_binding"]["status"], "development_reference_bound")
        self.assertFalse(result["vision_binding"]["mission_specific_observation"])

    def test_stored_whisper_prediction_preserves_asr_provenance(self) -> None:
        prediction = next(
            row for row in load_whisper_predictions(WHISPER_PATH) if row["id"] == "audio_008"
        )

        result = run_integrated_prototype(
            {"input_type": "whisper_prediction", "prediction": prediction},
            intent_system="deterministic_primary",
            **_inputs(),
        )

        self.assertEqual(result["status"], "active")
        self.assertEqual(result["input"]["record_id"], "audio_008")
        self.assertEqual(result["input"]["model_name"], "whisper")
        self.assertEqual(result["input"]["model_version"], "base")
        self.assertEqual(result["intent"]["parser"], "deterministic_v3")

    def test_missing_vision_artifact_is_rejected(self) -> None:
        inputs = _inputs()
        inputs["vision_artifact"] = {}

        with self.assertRaisesRegex(ValueError, "vision artifact"):
            run_integrated_prototype(
                {"input_type": "typed", "text": "Inspect the greenhouse."},
                intent_system="deterministic_primary",
                **inputs,
            )


if __name__ == "__main__":
    unittest.main()
