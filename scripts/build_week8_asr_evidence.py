"""Build the Week 8 ASR evidence record from stored Whisper outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.week8_asr import build_week8_asr_evidence, exactly_one_record  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "outputs/evaluations/week8_exact_scenario_asr.json",
    )
    args = parser.parse_args()
    manifest = exactly_one_record(_read_jsonl(args.manifest), name="manifest")
    prediction = exactly_one_record(_read_jsonl(args.predictions), name="predictions")
    evaluation_payload = json.loads(args.evaluation.read_text(encoding="utf-8"))
    evaluation = exactly_one_record(evaluation_payload.get("records", []), name="evaluation")
    result = build_week8_asr_evidence(manifest, prediction, evaluation)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["metrics"], indent=2, sort_keys=True))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


if __name__ == "__main__":
    main()
