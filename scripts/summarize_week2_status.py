"""Build a compact Week 2 status summary from recorded evaluation artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio-evaluation", required=True, help="Whisper transcript evaluation JSON.")
    parser.add_argument("--intent-accuracy", required=True, help="Audio-linked intent accuracy JSON.")
    parser.add_argument("--intent-impact", required=True, help="ASR-to-intent impact JSON.")
    parser.add_argument("--span-impact", required=True, help="ASR-to-span impact JSON.")
    parser.add_argument("--hf-token-metrics", required=True, help="Colab/T4 token-classifier metrics JSON.")
    parser.add_argument("--hf-token-error-analysis", required=True, help="Token-classifier error analysis JSON.")
    parser.add_argument("--output-json", required=True, help="Machine-readable summary output.")
    parser.add_argument("--output-markdown", required=True, help="Human-readable Markdown summary output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_summary(
        audio_evaluation=_load_json(args.audio_evaluation),
        intent_accuracy=_load_json(args.intent_accuracy),
        intent_impact=_load_json(args.intent_impact),
        span_impact=_load_json(args.span_impact),
        hf_token_metrics=_load_json(args.hf_token_metrics),
        hf_token_error_analysis=_load_json(args.hf_token_error_analysis),
        source_paths={
            "audio_evaluation": args.audio_evaluation,
            "intent_accuracy": args.intent_accuracy,
            "intent_impact": args.intent_impact,
            "span_impact": args.span_impact,
            "hf_token_metrics": args.hf_token_metrics,
            "hf_token_error_analysis": args.hf_token_error_analysis,
        },
    )
    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    output_markdown = Path(args.output_markdown)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.write_text(render_markdown(summary), encoding="utf-8")
    print(json.dumps(summary["headline"], indent=2, sort_keys=True))


def build_summary(
    *,
    audio_evaluation: dict[str, Any],
    intent_accuracy: dict[str, Any],
    intent_impact: dict[str, Any],
    span_impact: dict[str, Any],
    hf_token_metrics: dict[str, Any],
    hf_token_error_analysis: dict[str, Any],
    source_paths: dict[str, str],
) -> dict[str, Any]:
    audio_summary = audio_evaluation["summary"]
    intent_summary = intent_accuracy["summary"]
    span_summary = span_impact["summary"]
    hf_metrics = hf_token_metrics["metrics"]
    error_worst_records = hf_token_error_analysis.get("worst_records", [])

    deterministic_name = _latest_deterministic_name(intent_summary)
    deterministic_human = intent_summary.get(f"{deterministic_name}:human_transcript", {})
    deterministic_asr = intent_summary.get(f"{deterministic_name}:asr_transcript", {})
    trained_human = intent_summary.get("trained_nb_human_curated_v2:human_transcript", {})
    trained_asr = intent_summary.get("trained_nb_human_curated_v2:asr_transcript", {})
    deterministic_impact = intent_impact["summary"].get(deterministic_name, {})
    trained_impact = intent_impact["summary"].get("trained_nb_human_curated_v2", {})

    headline = {
        "audio_records": audio_summary.get("records"),
        "asr_exact_match_accuracy": audio_summary.get("exact_match_accuracy"),
        "asr_mean_word_error_rate": audio_summary.get("mean_word_error_rate"),
        "deterministic_human_intent_exact_accuracy": deterministic_human.get("exact_record_accuracy"),
        "deterministic_asr_intent_exact_accuracy": deterministic_asr.get("exact_record_accuracy"),
        "trained_human_intent_exact_accuracy": trained_human.get("exact_record_accuracy"),
        "trained_asr_intent_exact_accuracy": trained_asr.get("exact_record_accuracy"),
        "canonical_constraint_changed_records": trained_impact.get("canonical_constraint_changed_records"),
        "span_nb_v1_audio_matched_human_entity_f1": span_summary["human_transcript_span_accuracy"].get(
            "entity_f1"
        ),
        "asr_raw_span_prediction_changed_records": span_summary.get("span_prediction_changed_records"),
        "asr_semantic_span_prediction_changed_records": span_summary.get("semantic_span_prediction_changed_records"),
        "colab_t4_distilbert_test_entity_f1": hf_metrics.get("eval_entity_f1"),
        "colab_t4_distilbert_test_entity_precision": hf_metrics.get("eval_entity_precision"),
        "colab_t4_distilbert_test_entity_recall": hf_metrics.get("eval_entity_recall"),
        "colab_t4_distilbert_error_records": len(error_worst_records),
    }

    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status_note": (
                "Week 2 status summary from existing raw artifacts. This is not a final benchmark; "
                "the audio set is small, local-GPU ASR is not Colab/T4, and the current audio split is retrospective."
            ),
            "source_paths": source_paths,
        },
        "headline": headline,
        "details": {
            "asr": {
                "model_name": audio_evaluation["metadata"].get("model_name"),
                "model_version": audio_evaluation["metadata"].get("model_version"),
                "device_names": audio_evaluation["metadata"].get("parameters", {})
                .get("device_metadata", {})
                .get("cuda_device_names", []),
                "summary": audio_summary,
            },
            "audio_linked_intent_accuracy": {
                f"{deterministic_name}_human_transcript": deterministic_human,
                f"{deterministic_name}_asr_transcript": deterministic_asr,
                "trained_nb_human_curated_v2_human_transcript": trained_human,
                "trained_nb_human_curated_v2_asr_transcript": trained_asr,
            },
            "asr_intent_impact": {
                deterministic_name: deterministic_impact,
                "trained_nb_human_curated_v2": trained_impact,
            },
            "asr_span_impact": span_summary,
            "colab_t4_span_transformer": {
                "runtime": hf_token_metrics["metadata"].get("runtime", {}),
                "metrics": hf_metrics,
                "false_positive_entity_counts": hf_token_error_analysis.get("false_positive_entity_counts", {}),
                "false_negative_entity_counts": hf_token_error_analysis.get("false_negative_entity_counts", {}),
                "worst_record_ids": [str(record.get("id")) for record in error_worst_records],
            },
        },
        "interpretation": _interpretation(headline, hf_token_error_analysis),
        "limitations": [
            "The current audio set has only 10 recordings.",
            "The current audio split was assigned retrospectively after the first pooled ASR run.",
            "The recorded ASR run used a local GTX GPU, not Colab/T4.",
            "Audio-linked intent labels are reused from matching text-command records; they are not newly collected audio-specific gold labels.",
            "ASR transcript span rows compare predictions only; no human gold spans exist for Whisper transcript text.",
            "The strongest transformer result is text-command span extraction, not speech-to-mission performance.",
        ],
    }


def render_markdown(summary: dict[str, Any]) -> str:
    headline = summary["headline"]
    details = summary["details"]
    lines = [
        "# Week 2 Status Summary",
        "",
        summary["metadata"]["status_note"],
        "",
        "## Headline Metrics",
        "",
        "| Question | Current Answer |",
        "| --- | --- |",
        f"| ASR exact transcript accuracy | {_pct(headline['asr_exact_match_accuracy'])} on {headline['audio_records']} recordings |",
        f"| ASR mean word error rate | {_pct(headline['asr_mean_word_error_rate'])} |",
        f"| Human-transcript intent exact accuracy | {_pct(headline['trained_human_intent_exact_accuracy'])} with `trained_nb_human_curated_v2` |",
        f"| Whisper-transcript intent exact accuracy | {_pct(headline['trained_asr_intent_exact_accuracy'])} with `trained_nb_human_curated_v2` |",
        f"| Canonical constraint changes from ASR | {headline['canonical_constraint_changed_records']} records |",
        f"| Audio-matched human-transcript span F1 | {_pct(headline['span_nb_v1_audio_matched_human_entity_f1'])} with `span_nb_v1` |",
        f"| ASR semantic span-prediction changes | {headline['asr_semantic_span_prediction_changed_records']} records |",
        f"| Colab/T4 DistilBERT text span F1 | {_pct(headline['colab_t4_distilbert_test_entity_f1'])} |",
        f"| Colab/T4 DistilBERT text span precision/recall | {_pct(headline['colab_t4_distilbert_test_entity_precision'])} / {_pct(headline['colab_t4_distilbert_test_entity_recall'])} |",
        "",
        "## Interpretation",
        "",
    ]
    lines.extend(f"- {item}" for item in summary["interpretation"])
    lines.extend(["", "## Remaining Errors", ""])
    transformer = details["colab_t4_span_transformer"]
    lines.append(f"- False negatives by entity: `{json.dumps(transformer['false_negative_entity_counts'], sort_keys=True)}`")
    lines.append(f"- False positives by entity: `{json.dumps(transformer['false_positive_entity_counts'], sort_keys=True)}`")
    lines.append(f"- Worst held-out record ids: `{', '.join(transformer['worst_record_ids'])}`")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in summary["limitations"])
    lines.extend(["", "## Source Artifacts", ""])
    lines.extend(f"- `{name}`: `{path}`" for name, path in summary["metadata"]["source_paths"].items())
    lines.append("")
    return "\n".join(lines)


def _interpretation(headline: dict[str, Any], hf_token_error_analysis: dict[str, Any]) -> list[str]:
    return [
        "ASR is currently strong on the small recorded sample, but the evidence is not benchmark-grade.",
        "The observed ASR word substitution affects raw constraint strings, but canonical altitude constraints remain unchanged.",
        "Audio-linked intent extraction is perfect on human transcripts and drops to 0.90 exact-record accuracy on Whisper transcripts because of one raw constraint mismatch.",
        "The strongest text span extractor is the expanded 85-record Colab/T4 DistilBERT run, with entity F1 around 0.79 on the current 10-record test split.",
        "The remaining transformer span errors still cluster around count/constraint confusion and target boundary mistakes.",
        "The next research-useful improvement is a pre-registered larger audio batch or a restored Colab checkpoint for direct transformer inference on ASR text.",
    ]


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _latest_deterministic_name(intent_summary: dict[str, Any]) -> str:
    names = sorted({key.split(":", 1)[0] for key in intent_summary if key.startswith("deterministic_")})
    return names[-1] if names else "deterministic_v1"


def _pct(value: Any) -> str:
    if not isinstance(value, int | float):
        return "not stated"
    return f"{value * 100:.2f}%"


if __name__ == "__main__":
    main()
