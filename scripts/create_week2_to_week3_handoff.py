"""Create the Week 2 NLP handoff contract for Week 3 grounding."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


PROVISIONAL_SYSTEM = "deterministic_v3"
TRANSFORMER_SYSTEMS = ("span_intent_assembly", "hybrid_span_parser")
INTENT_FIELDS = ("action", "count", "location", "target", "constraints")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intent-accuracy", required=True, help="Reviewed audio intent accuracy JSON.")
    parser.add_argument(
        "--transformer-human-intent-accuracy",
        required=True,
        help="Transformer transcript-intent accuracy JSON for human/reference transcripts.",
    )
    parser.add_argument(
        "--transformer-asr-intent-accuracy",
        required=True,
        help="Transformer transcript-intent accuracy JSON for ASR/Whisper transcripts.",
    )
    parser.add_argument("--remediation-packet", required=True, help="Audio span remediation packet JSONL.")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-markdown", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    handoff = build_handoff(
        intent_accuracy=_load_json(args.intent_accuracy),
        transformer_human_intent_accuracy=_load_json(args.transformer_human_intent_accuracy),
        transformer_asr_intent_accuracy=_load_json(args.transformer_asr_intent_accuracy),
        remediation_records=_load_jsonl(args.remediation_packet),
        source_paths={
            "intent_accuracy": args.intent_accuracy,
            "transformer_human_intent_accuracy": args.transformer_human_intent_accuracy,
            "transformer_asr_intent_accuracy": args.transformer_asr_intent_accuracy,
            "remediation_packet": args.remediation_packet,
        },
    )

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(handoff, indent=2, sort_keys=True), encoding="utf-8")

    output_markdown = Path(args.output_markdown)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.write_text(render_markdown(handoff), encoding="utf-8")
    print(json.dumps(handoff["summary"], indent=2, sort_keys=True))


def build_handoff(
    *,
    intent_accuracy: dict[str, Any],
    transformer_human_intent_accuracy: dict[str, Any],
    transformer_asr_intent_accuracy: dict[str, Any],
    remediation_records: list[dict[str, Any]],
    source_paths: dict[str, str],
) -> dict[str, Any]:
    intent_summary = intent_accuracy.get("summary", {})
    transformer_human_summary = transformer_human_intent_accuracy.get("summary", {})
    transformer_asr_summary = transformer_asr_intent_accuracy.get("summary", {})

    provisional_human = intent_summary.get(f"{PROVISIONAL_SYSTEM}:human_transcript", {})
    provisional_asr = intent_summary.get(f"{PROVISIONAL_SYSTEM}:asr_transcript", {})
    transformer_comparison = {
        "human_transcript": _system_accuracy_summary(transformer_human_summary),
        "asr_transcript": _system_accuracy_summary(transformer_asr_summary),
    }

    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_paths": source_paths,
            "note": (
                "Week 2 NLP handoff contract for Week 3 grounding. This is a development handoff, "
                "not a claim that NLP is solved or that the pipeline has end-to-end real-world evidence."
            ),
        },
        "summary": {
            "handoff_ready_for_week3_grounding": True,
            "provisional_primary_intent_system": PROVISIONAL_SYSTEM,
            "intent_fields": list(INTENT_FIELDS),
            "human_transcript_records": provisional_human.get("records"),
            "human_transcript_exact_accuracy": provisional_human.get("exact_record_accuracy"),
            "asr_transcript_records": provisional_asr.get("records"),
            "asr_transcript_exact_accuracy": provisional_asr.get("exact_record_accuracy"),
            "transformer_span_path_primary": False,
            "span_remediation_records": len(remediation_records),
        },
        "handoff_contract": {
            "week3_input": (
                "A typed command string, human/reference transcript, or Whisper transcript that has been parsed "
                "into the bounded Week 2 intent fields."
            ),
            "week3_output_needed": (
                "A grounded representation mapping intent location/target phrases to documented map records "
                "and coordinates, with ambiguity or missing-grounding status."
            ),
            "primary_intent_path": PROVISIONAL_SYSTEM,
            "intent_schema": {
                "action": "string or null",
                "count": "integer, 'all', or null",
                "location": "string or null",
                "target": "string or null",
                "constraints": "list of strings",
            },
            "required_week3_validation": [
                "Reject or mark intents with both location and target missing when grounding requires a place.",
                "Do not silently invent coordinates for unknown location or target phrases.",
                "Preserve the original command/transcript and parser name in grounding outputs.",
                "Record whether grounding came from a map record, alias, or unresolved phrase.",
            ],
            "not_yet_handoff_primary": {
                "transformer_span_paths": list(TRANSFORMER_SYSTEMS),
                "reason": (
                    "On the 30-record audio_v2_holdout diagnostic benchmark, transformer span-to-intent "
                    "accuracy is much lower than deterministic_v3 for final intent JSON."
                ),
            },
        },
        "evidence": {
            "provisional_primary": {
                "human_transcript": provisional_human,
                "asr_transcript": provisional_asr,
                "caveat": (
                    "The current primary intent path is selected for a bounded synthetic-simulation handoff. "
                    "The fresh post-development benchmark is cleaner than the earlier same-batch artifacts, "
                    "but it is still small and does not prove broad language understanding."
                ),
            },
            "transformer_transcript_intent": transformer_comparison,
            "span_remediation": {
                "records": len(remediation_records),
                "failed_field_counts": _failed_field_counts(remediation_records),
                "label_status_counts": _label_status_counts(remediation_records),
                "caveat": "The remediation packet has blank spans and is not gold data until human-reviewed.",
            },
        },
        "week3_known_blockers": [
            "No blockers remain for the Week 3 synthetic-map completion gate.",
            "Real/public map provenance remains deferred before any real-world grounding claim.",
            "Semantic-map, retrieval-based, and learned grounding baselines are not implemented.",
            "Route geometry and safety enforcement remain later-module responsibilities.",
        ],
        "week2_carry_forward_debt": [
            "A fresh non-overlapping audio/text packet was validated before treating it as generalized; keep the result bounded to this small benchmark.",
            "Human-review the 24-record audio span remediation packet if the transformer span path should improve.",
            "Keep ASR evaluation separate from intent and grounding evaluation.",
        ],
    }


def render_markdown(handoff: dict[str, Any]) -> str:
    summary = handoff["summary"]
    evidence = handoff["evidence"]
    lines = [
        "# Week 2 NLP Handoff To Week 3 Grounding",
        "",
        handoff["metadata"]["note"],
        "",
        "## Decision",
        "",
        f"- Handoff ready for Week 3 grounding: `{summary['handoff_ready_for_week3_grounding']}`",
        f"- Provisional primary intent system: `{summary['provisional_primary_intent_system']}`",
        f"- Human/reference transcript exact accuracy: `{_fmt_pct(summary['human_transcript_exact_accuracy'])}` on `{summary['human_transcript_records']}` records",
        f"- ASR/Whisper transcript exact accuracy: `{_fmt_pct(summary['asr_transcript_exact_accuracy'])}` on `{summary['asr_transcript_records']}` records",
        f"- Transformer span path is primary: `{summary['transformer_span_path_primary']}`",
        f"- Span remediation records: `{summary['span_remediation_records']}`",
        "",
        "## Week 3 Contract",
        "",
        f"- Input: {handoff['handoff_contract']['week3_input']}",
        f"- Output needed: {handoff['handoff_contract']['week3_output_needed']}",
        f"- Intent fields: `{', '.join(summary['intent_fields'])}`",
        "",
        "## Required Grounding Validation",
        "",
    ]
    lines.extend(f"- {item}" for item in handoff["handoff_contract"]["required_week3_validation"])
    lines.extend(
        [
            "",
            "## Evidence Caveats",
            "",
            f"- {evidence['provisional_primary']['caveat']}",
            f"- {evidence['span_remediation']['caveat']}",
            f"- Transformer transcript-intent summary: `{json.dumps(evidence['transformer_transcript_intent'], sort_keys=True)}`",
            "",
            "## Week 3 Synthetic-Scope Status",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in handoff["week3_known_blockers"])
    lines.extend(["", "## Carry-Forward Week 2 Debt", ""])
    lines.extend(f"- {item}" for item in handoff["week2_carry_forward_debt"])
    lines.extend(["", "## Source Artifacts", ""])
    lines.extend(f"- `{name}`: `{path}`" for name, path in handoff["metadata"]["source_paths"].items())
    lines.append("")
    return "\n".join(lines)


def _system_accuracy_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        system_name: {
            "records": system_summary.get("records"),
            "exact_record_accuracy": system_summary.get("exact_record_accuracy"),
            "field_accuracy": system_summary.get("field_accuracy"),
            "field_error_counts": system_summary.get("field_error_counts", {}),
        }
        for system_name, system_summary in sorted(summary.items())
        if system_name in {PROVISIONAL_SYSTEM, *TRANSFORMER_SYSTEMS}
    }


def _failed_field_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for field in record.get("failed_intent_fields", []):
            counts[str(field)] = counts.get(str(field), 0) + 1
    return dict(sorted(counts.items()))


def _label_status_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        status = str(record.get("label_status", "not stated"))
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _fmt_pct(value: Any) -> str:
    return f"{value * 100:.2f}%" if isinstance(value, int | float) else "not stated"


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


if __name__ == "__main__":
    main()
