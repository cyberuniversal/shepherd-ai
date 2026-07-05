"""Audit why Week 2 metrics may be high and where the evidence is still weak."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.audio_manifest import load_audio_manifest  # noqa: E402
from shepherd_ai.intent_training import load_intent_model, load_labeled_commands  # noqa: E402
from shepherd_ai.span_annotations import load_span_labeled_commands  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commands", required=True, help="Curated intent command JSONL.")
    parser.add_argument("--spans", required=True, help="Human-verified span command JSONL.")
    parser.add_argument("--audio-manifest", required=True, help="Audio manifest JSONL.")
    parser.add_argument("--dataset-root", required=True, help="Root directory for audio manifest validation.")
    parser.add_argument("--status-summary", required=True, help="Week 2 status summary JSON.")
    parser.add_argument("--intent-model", required=True, help="Saved trained intent model JSON.")
    parser.add_argument("--output-json", required=True, help="Machine-readable audit output.")
    parser.add_argument("--output-markdown", required=True, help="Human-readable audit output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    command_records = load_labeled_commands(args.commands)
    command_label_sources = _raw_label_sources(args.commands)
    span_records = load_span_labeled_commands(args.spans)
    audio_records = load_audio_manifest(args.audio_manifest, dataset_root=args.dataset_root)
    status_summary = _load_json(args.status_summary)
    intent_model = load_intent_model(args.intent_model)

    audit = build_audit(
        command_records=command_records,
        span_records=span_records,
        audio_records=audio_records,
        status_summary=status_summary,
        intent_model_payload=intent_model.to_dict(),
        command_label_sources=command_label_sources,
        source_paths={
            "commands": args.commands,
            "spans": args.spans,
            "audio_manifest": args.audio_manifest,
            "status_summary": args.status_summary,
            "intent_model": args.intent_model,
        },
    )

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")

    output_markdown = Path(args.output_markdown)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.write_text(render_markdown(audit), encoding="utf-8")
    print(json.dumps(audit["summary"], indent=2, sort_keys=True))


def build_audit(
    *,
    command_records: list[Any],
    span_records: list[Any],
    audio_records: list[Any],
    status_summary: dict[str, Any],
    intent_model_payload: dict[str, Any],
    command_label_sources: Counter[str],
    source_paths: dict[str, str],
) -> dict[str, Any]:
    command_text_index = _text_index(command_records)
    span_text_index = _text_index(span_records)
    command_split_duplicates = _duplicates_across_splits(command_records)
    span_split_duplicates = _duplicates_across_splits(span_records)
    audio_command_overlaps = _audio_overlaps(audio_records, command_text_index)
    audio_span_overlaps = _audio_overlaps(audio_records, span_text_index)
    span_sources = Counter(record.source for record in span_records)

    risk_factors = _risk_factors(
        command_records=command_records,
        span_records=span_records,
        audio_records=audio_records,
        status_summary=status_summary,
        intent_model_payload=intent_model_payload,
        command_split_duplicates=command_split_duplicates,
        span_split_duplicates=span_split_duplicates,
        audio_command_overlaps=audio_command_overlaps,
        audio_span_overlaps=audio_span_overlaps,
        command_label_sources=command_label_sources,
        span_sources=span_sources,
    )

    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "note": (
                "Performance-risk audit only. These findings explain why current Week 2 metrics can be high; "
                "they do not invalidate the artifacts, but they limit claim strength."
            ),
            "source_paths": source_paths,
        },
        "summary": {
            "command_records": len(command_records),
            "span_records": len(span_records),
            "audio_records": len(audio_records),
            "audio_transcripts_matching_command_records": len(audio_command_overlaps),
            "audio_transcripts_matching_span_records": len(audio_span_overlaps),
            "command_duplicate_texts_across_splits": len(command_split_duplicates),
            "span_duplicate_texts_across_splits": len(span_split_duplicates),
            "risk_factor_count": len(risk_factors),
        },
        "dataset_profile": {
            "command_split_counts": _split_counts(command_records),
            "span_split_counts": _split_counts(span_records),
            "audio_split_counts": _split_counts(audio_records),
            "command_label_sources": dict(sorted(command_label_sources.items())),
            "span_sources": dict(sorted(span_sources.items())),
            "intent_model_parameters": intent_model_payload.get("parameters", {}),
            "headline_metrics": status_summary.get("headline", {}),
        },
        "overlap": {
            "audio_command_overlaps": audio_command_overlaps,
            "audio_span_overlaps": audio_span_overlaps,
            "command_duplicate_texts_across_splits": command_split_duplicates,
            "span_duplicate_texts_across_splits": span_split_duplicates,
        },
        "risk_factors": risk_factors,
        "why_metrics_are_high": [
            "The current command language is short, schema-like, and close to the known Week 2 fields.",
            "All currently evaluated audio transcripts match commands already present in the curated text and span datasets.",
            "The ASR sample is clean and tiny, so one substitution dominates the measured speech error.",
            "The strongest intent model is hybrid: it uses deterministic rule overrides for action, location, target, count, and constraints.",
            "The expanded span dataset includes targeted follow-up records derived from earlier error analysis, which can improve known failure modes.",
            "The held-out span test split has only 10 records, so each record has large influence on F1.",
        ],
        "what_would_make_the_claim_stronger": [
            "Collect a larger pre-registered audio batch before running ASR.",
            "Use commands that do not overlap existing training, validation, or test texts.",
            "Preserve human labels from at least one reviewer instead of assistant-curated labels only.",
            "Evaluate the Colab/T4 transformer checkpoint directly on human transcripts and ASR transcripts once checkpoint artifacts are restored.",
            "Create a fresh held-out span test set after targeted follow-up data collection.",
        ],
    }


def render_markdown(audit: dict[str, Any]) -> str:
    summary = audit["summary"]
    profile = audit["dataset_profile"]
    lines = [
        "# Week 2 Performance Risk Audit",
        "",
        audit["metadata"]["note"],
        "",
        "## Why It Looks Good",
        "",
    ]
    lines.extend(f"- {item}" for item in audit["why_metrics_are_high"])
    lines.extend(
        [
            "",
            "## Evidence Profile",
            "",
            f"- Intent command records: {summary['command_records']} with splits `{json.dumps(profile['command_split_counts'], sort_keys=True)}`.",
            f"- Span command records: {summary['span_records']} with splits `{json.dumps(profile['span_split_counts'], sort_keys=True)}`.",
            f"- Audio records: {summary['audio_records']} with splits `{json.dumps(profile['audio_split_counts'], sort_keys=True)}`.",
            f"- Audio transcripts matching curated command records: {summary['audio_transcripts_matching_command_records']} / {summary['audio_records']}.",
            f"- Audio transcripts matching span records: {summary['audio_transcripts_matching_span_records']} / {summary['audio_records']}.",
            f"- Duplicate command texts across splits: {summary['command_duplicate_texts_across_splits']}.",
            f"- Duplicate span texts across splits: {summary['span_duplicate_texts_across_splits']}.",
            f"- Intent model uses rule overrides: `{profile['intent_model_parameters'].get('use_rule_overrides')}`.",
            "",
            "## Risk Factors",
            "",
        ]
    )
    lines.extend(f"- **{factor['severity']}** `{factor['id']}`: {factor['description']}" for factor in audit["risk_factors"])
    lines.extend(["", "## Stronger Next Evidence", ""])
    lines.extend(f"- {item}" for item in audit["what_would_make_the_claim_stronger"])
    lines.extend(["", "## Source Artifacts", ""])
    lines.extend(f"- `{name}`: `{path}`" for name, path in audit["metadata"]["source_paths"].items())
    lines.append("")
    return "\n".join(lines)


def _risk_factors(
    *,
    command_records: list[Any],
    span_records: list[Any],
    audio_records: list[Any],
    status_summary: dict[str, Any],
    intent_model_payload: dict[str, Any],
    command_split_duplicates: list[dict[str, Any]],
    span_split_duplicates: list[dict[str, Any]],
    audio_command_overlaps: list[dict[str, Any]],
    audio_span_overlaps: list[dict[str, Any]],
    command_label_sources: Counter[str],
    span_sources: Counter[str],
) -> list[dict[str, str]]:
    risks: list[dict[str, str]] = []
    headline = status_summary.get("headline", {})
    if len(audio_records) < 30:
        risks.append(_risk("small_audio_sample", "high", f"Only {len(audio_records)} audio records are evaluated."))
    if len(command_records) < 100:
        risks.append(_risk("small_intent_dataset", "medium", f"Only {len(command_records)} curated intent records exist."))
    if len(span_records) < 150:
        risks.append(_risk("small_span_dataset", "medium", f"Only {len(span_records)} span records exist."))
    if headline.get("audio_records") == len(audio_records):
        risks.append(
            _risk(
                "retrospective_audio_split",
                "high",
                "The current status summary notes a retrospective audio split, so ASR split metrics are not a clean final benchmark.",
            )
        )
    if len(audio_command_overlaps) == len(audio_records):
        risks.append(
            _risk(
                "audio_text_overlap",
                "high",
                "Every audio transcript matches at least one curated command-label record.",
            )
        )
    if len(audio_span_overlaps) == len(audio_records):
        risks.append(
            _risk(
                "audio_span_overlap",
                "medium",
                "Every audio transcript matches at least one human-verified span record.",
            )
        )
    if any("assistant" in source for source in command_label_sources):
        risks.append(
            _risk(
                "assistant_curated_intent_labels",
                "medium",
                "The curated intent labels are assistant-curated from user text, not independently human-adjudicated labels.",
            )
        )
    if bool(intent_model_payload.get("parameters", {}).get("use_rule_overrides")):
        risks.append(
            _risk(
                "hybrid_intent_model",
                "medium",
                "The strongest intent model uses deterministic rule overrides, so its score is not a pure learned-model result.",
            )
        )
    if any("v2" in source for source in span_sources):
        risks.append(
            _risk(
                "targeted_span_followup",
                "medium",
                "The expanded span dataset includes targeted follow-up records derived from earlier model errors.",
            )
        )
    if command_split_duplicates:
        risks.append(_risk("command_split_text_leakage", "high", "Duplicate command text appears across intent splits."))
    if span_split_duplicates:
        risks.append(_risk("span_split_text_leakage", "high", "Duplicate command text appears across span splits."))
    return risks


def _risk(risk_id: str, severity: str, description: str) -> dict[str, str]:
    return {"id": risk_id, "severity": severity, "description": description}


def _audio_overlaps(audio_records: list[Any], text_index: dict[str, list[Any]]) -> list[dict[str, Any]]:
    overlaps: list[dict[str, Any]] = []
    for record in audio_records:
        matches = text_index.get(_normalize_text(record.transcript), [])
        if matches:
            overlaps.append(
                {
                    "audio_id": record.id,
                    "split": record.split,
                    "matched_ids": [match.id for match in matches],
                    "matched_splits": sorted({match.split for match in matches}),
                }
            )
    return overlaps


def _duplicates_across_splits(records: list[Any]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Any]] = defaultdict(list)
    for record in records:
        grouped[_normalize_text(record.text)].append(record)
    duplicates: list[dict[str, Any]] = []
    for normalized_text, matches in sorted(grouped.items()):
        splits = sorted({match.split for match in matches})
        if len(splits) > 1:
            duplicates.append(
                {
                    "normalized_text": normalized_text,
                    "ids": [match.id for match in matches],
                    "splits": splits,
                }
            )
    return duplicates


def _text_index(records: list[Any]) -> dict[str, list[Any]]:
    grouped: dict[str, list[Any]] = defaultdict(list)
    for record in records:
        grouped[_normalize_text(record.text)].append(record)
    return dict(grouped)


def _split_counts(records: list[Any]) -> dict[str, int]:
    return dict(sorted(Counter(record.split for record in records).items()))


def _raw_label_sources(path: str | Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        counts[str(raw.get("label_source", "not stated"))] += 1
    return counts


def _normalize_text(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
