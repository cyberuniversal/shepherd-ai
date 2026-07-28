"""Run one Shepherd workflow through the imported DistilBERT span checkpoint."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations  # noqa: E402
from shepherd_ai.hf_span_predictor import (  # noqa: E402
    HfTokenClassifierSpanPredictor,
)
from shepherd_ai.integrated_prototype import run_integrated_prototype  # noqa: E402
from shepherd_ai.safety import load_safety_policy  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--map", type=Path, required=True)
    parser.add_argument("--fleet", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--vision-artifact", type=Path, required=True)
    parser.add_argument("--required-device-substring", default="")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    started = perf_counter()
    predictor = HfTokenClassifierSpanPredictor.from_model_dir(
        args.model_dir,
        required_device_substring=args.required_device_substring,
    )
    vision_payload = _read_object(args.vision_artifact)
    result = run_integrated_prototype(
        {"input_type": "typed", "text": args.command},
        intent_system="trained_distilbert_spans",
        locations=load_map_locations(args.map),
        fleet_payload=_read_object(args.fleet),
        safety_policy=load_safety_policy(args.policy),
        trained_intent_model=None,
        trained_span_predictor=predictor,
        vision_artifact={
            "artifact_path": _display_path(args.vision_artifact),
            "scope": "week6_development_result_not_mission_specific",
            "payload": vision_payload,
        },
    )
    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "runner": "trained_distilbert_span_integrated_prototype_v1",
            "intent_system": "trained_distilbert_spans",
            "command": args.command,
            "model": {
                **predictor.runtime_metadata,
                "model_dir": _display_path(args.model_dir),
            },
            "input_sha256": {
                "model_config": _sha256(args.model_dir / "config.json"),
                "model_weights": _weight_hash(args.model_dir),
                "map": _sha256(args.map),
                "fleet": _sha256(args.fleet),
                "policy": _sha256(args.policy),
                "vision_artifact": _sha256(args.vision_artifact),
            },
            "elapsed_seconds": perf_counter() - started,
            "claim_status": "wiring_smoke_test_not_paper_evidence",
        },
        "result": result,
    }
    if not str(result["intent"]["parser"]).startswith("hf_token_classifier:"):
        raise RuntimeError("trained span checkpoint was not the invoked intent component")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "intent_parser": result["intent"]["parser"],
                "device": predictor.runtime_metadata["device_name"],
                "output": str(args.output),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_object(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON input must contain an object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _weight_hash(model_dir: Path) -> str:
    for name in ("model.safetensors", "pytorch_model.bin"):
        path = model_dir / name
        if path.is_file():
            return _sha256(path)
    raise ValueError(f"model directory has no supported weight file: {model_dir}")


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return str(resolved)


if __name__ == "__main__":
    main()
