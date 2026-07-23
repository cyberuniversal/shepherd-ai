"""Contracts for collecting and freezing a human evidence-decision benchmark."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from shepherd_ai.monolithic_decision import (
    PROMPT_VERSION,
    build_messages,
    messages_sha256,
    validate_input_record,
)


DECISIONS = {"proceed", "clarify", "block"}
STAGES = {
    "grounding_sufficiency",
    "preflight",
    "compound_grounding_and_preflight",
}
AUTHOR_REQUIRED_FIELDS = {
    "id",
    "text",
    "decision_stage",
    "context_id",
    "author_decision",
    "author_rationale",
    "split",
    "source",
    "data_type",
    "author_id",
}
CONTEXT_REQUIRED_FIELDS = {
    "context_id",
    "decision_stage",
    "stage_definition",
    "evidence",
    "source",
    "data_type",
}
REVIEW_REQUIRED_FIELDS = {
    "id",
    "reviewer_id",
    "reviewer_decision",
    "reviewer_rationale",
}
ADJUDICATION_REQUIRED_FIELDS = {
    "id",
    "adjudicator_id",
    "final_decision",
    "adjudication_rationale",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"JSONL input must contain at least one object: {path}")
    return rows


def write_jsonl(rows: Iterable[Mapping[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(dict(row), ensure_ascii=True, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def context_sha256(context: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(context),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def index_contexts(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    contexts: dict[str, dict[str, Any]] = {}
    for line_number, row in enumerate(rows, start=1):
        _require_fields(row, CONTEXT_REQUIRED_FIELDS, f"context line {line_number}")
        context_id = _nonempty(row["context_id"], "context_id")
        stage = _decision_stage(row["decision_stage"])
        if context_id in contexts:
            raise ValueError(f"duplicate context_id: {context_id}")
        if not isinstance(row["evidence"], dict):
            raise ValueError(f"{context_id}: evidence must be an object")
        if not _nonempty(row["stage_definition"], "stage_definition"):
            raise ValueError(f"{context_id}: stage_definition must be non-empty")
        contexts[context_id] = {**row, "decision_stage": stage}
    return contexts


def prepare_blinded_review(
    author_rows: Iterable[dict[str, Any]],
    contexts: Mapping[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    packet: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_texts: set[str] = set()
    for line_number, row in enumerate(author_rows, start=1):
        _require_fields(row, AUTHOR_REQUIRED_FIELDS, f"author line {line_number}")
        case_id = _nonempty(row["id"], "id")
        text = _nonempty(row["text"], "text")
        stage = _decision_stage(row["decision_stage"])
        _decision(row["author_decision"], "author_decision")
        _nonempty(row["author_rationale"], "author_rationale")
        _nonempty(row["author_id"], "author_id")
        if row["split"] != "final_test":
            raise ValueError(f"{case_id}: split must be 'final_test'")
        if row["data_type"] != "human_written_evidence_decision":
            raise ValueError(
                f"{case_id}: data_type must be 'human_written_evidence_decision'"
            )
        normalized = normalize_text(text)
        if case_id in seen_ids:
            raise ValueError(f"duplicate case id: {case_id}")
        if normalized in seen_texts:
            raise ValueError(f"{case_id}: duplicate normalized command text")
        seen_ids.add(case_id)
        seen_texts.add(normalized)
        context = _matching_context(row, contexts, stage)
        packet.append(
            {
                "id": case_id,
                "text": text,
                "decision_stage": stage,
                "context_id": context["context_id"],
                "stage_definition": context["stage_definition"],
                "evidence": context["evidence"],
                "context_sha256": context_sha256(context),
            }
        )
    return packet


def adjudicate_records(
    author_rows: Iterable[dict[str, Any]],
    review_rows: Iterable[dict[str, Any]],
    contexts: Mapping[str, dict[str, Any]],
    adjudication_rows: Iterable[dict[str, Any]] = (),
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    author_list = list(author_rows)
    prepare_blinded_review(author_list, contexts)
    authors = _index_unique(author_list, "id", "author")
    reviews = _index_unique(review_rows, "id", "review")
    adjudications = _index_unique(adjudication_rows, "id", "adjudication")
    missing_reviews = sorted(set(authors) - set(reviews))
    extra_reviews = sorted(set(reviews) - set(authors))
    if missing_reviews or extra_reviews:
        raise ValueError(
            f"review IDs do not match author IDs; missing={missing_reviews}, "
            f"extra={extra_reviews}"
        )

    final_rows: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []
    for case_id, author in authors.items():
        _require_fields(author, AUTHOR_REQUIRED_FIELDS, f"author {case_id}")
        review = reviews[case_id]
        _require_fields(review, REVIEW_REQUIRED_FIELDS, f"review {case_id}")
        author_id = _nonempty(author["author_id"], "author_id")
        reviewer_id = _nonempty(review["reviewer_id"], "reviewer_id")
        if author_id == reviewer_id:
            raise ValueError(f"{case_id}: author_id and reviewer_id must differ")
        author_decision = _decision(author["author_decision"], "author_decision")
        reviewer_decision = _decision(
            review["reviewer_decision"], "reviewer_decision"
        )
        _nonempty(review["reviewer_rationale"], "reviewer_rationale")
        stage = _decision_stage(author["decision_stage"])
        context = _matching_context(author, contexts, stage)
        if author_decision == reviewer_decision:
            final_decision = author_decision
            rationale = str(review["reviewer_rationale"]).strip()
            resolution = "independent_agreement"
        else:
            disagreement = {
                "id": case_id,
                "text": author["text"],
                "context_id": author["context_id"],
                "decision_stage": stage,
                "author_decision": author_decision,
                "author_rationale": author["author_rationale"],
                "reviewer_decision": reviewer_decision,
                "reviewer_rationale": review["reviewer_rationale"],
            }
            disagreements.append(disagreement)
            adjudication = adjudications.get(case_id)
            if adjudication is None:
                continue
            _require_fields(
                adjudication,
                ADJUDICATION_REQUIRED_FIELDS,
                f"adjudication {case_id}",
            )
            adjudicator_id = _nonempty(
                adjudication["adjudicator_id"], "adjudicator_id"
            )
            if adjudicator_id in {author_id, reviewer_id}:
                raise ValueError(
                    f"{case_id}: adjudicator_id must differ from author and reviewer"
                )
            final_decision = _decision(
                adjudication["final_decision"], "final_decision"
            )
            rationale = _nonempty(
                adjudication["adjudication_rationale"],
                "adjudication_rationale",
            )
            resolution = "third_party_adjudication"

        final_rows.append(
            {
                "id": case_id,
                "text": str(author["text"]).strip(),
                "decision_stage": stage,
                "context_id": str(author["context_id"]).strip(),
                "context_sha256": context_sha256(context),
                "expected_decision": final_decision,
                "label_rationale": rationale,
                "split": "final_test",
                "source": str(author["source"]).strip(),
                "data_type": "human_written_evidence_decision",
                "author_id": author_id,
                "reviewer_id": reviewer_id,
                "label_status": "adjudicated",
                "label_resolution": resolution,
            }
        )
    disagreement_ids = {row["id"] for row in disagreements}
    extra_adjudications = sorted(set(adjudications) - disagreement_ids)
    if extra_adjudications:
        raise ValueError(
            f"adjudications supplied for cases without disagreement: "
            f"{extra_adjudications}"
        )
    unresolved = disagreement_ids - set(adjudications)
    disagreements = [
        {
            **row,
            "status": (
                "requires_third_party_adjudication"
                if row["id"] in unresolved
                else "adjudicated"
            ),
        }
        for row in disagreements
    ]
    return final_rows, disagreements


def build_model_packet(
    benchmark_rows: Iterable[dict[str, Any]],
    contexts: Mapping[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inputs: list[dict[str, Any]] = []
    gold: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in benchmark_rows:
        case_id = _nonempty(row.get("id"), "id")
        if case_id in seen_ids:
            raise ValueError(f"duplicate case id: {case_id}")
        seen_ids.add(case_id)
        stage = _decision_stage(row.get("decision_stage"))
        context = _matching_context(row, contexts, stage)
        expected_hash = context_sha256(context)
        if row.get("context_sha256") != expected_hash:
            raise ValueError(f"{case_id}: frozen context hash mismatch")
        expected_decision = _decision(
            row.get("expected_decision"), "expected_decision"
        )
        if row.get("split") != "final_test":
            raise ValueError(f"{case_id}: split must be 'final_test'")
        if row.get("data_type") != "human_written_evidence_decision":
            raise ValueError(
                f"{case_id}: data_type must be 'human_written_evidence_decision'"
            )
        if row.get("label_status") != "adjudicated":
            raise ValueError(f"{case_id}: label_status must be 'adjudicated'")
        author_id = _nonempty(row.get("author_id"), "author_id")
        reviewer_id = _nonempty(row.get("reviewer_id"), "reviewer_id")
        if author_id == reviewer_id:
            raise ValueError(f"{case_id}: author_id and reviewer_id must differ")
        _nonempty(row.get("label_rationale"), "label_rationale")
        record = {
            "case_id": case_id,
            "stratum": "fresh_human_evidence_decision",
            "data_type": row.get("data_type"),
            "decision_stage": stage,
            "stage_definition": context["stage_definition"],
            "command": _nonempty(row.get("text"), "text"),
            "evidence": context["evidence"],
            "context_id": context["context_id"],
            "context_sha256": expected_hash,
        }
        messages = build_messages(record)
        input_record = {
            **record,
            "prompt_version": PROMPT_VERSION,
            "messages": messages,
            "prompt_sha256": messages_sha256(messages),
        }
        validate_input_record(input_record)
        inputs.append(input_record)
        gold.append(
            {
                "case_id": case_id,
                "stratum": "fresh_human_evidence_decision",
                "data_type": row.get("data_type"),
                "expected_decision": expected_decision,
                "context_id": context["context_id"],
                "context_sha256": expected_hash,
            }
        )
    return inputs, gold


def decision_counts(rows: Iterable[Mapping[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row[field]) for row in rows).items()))


def normalize_text(text: str) -> str:
    return " ".join("".join(char if char.isalnum() else " " for char in text.lower()).split())


def _matching_context(
    row: Mapping[str, Any],
    contexts: Mapping[str, dict[str, Any]],
    stage: str,
) -> dict[str, Any]:
    context_id = _nonempty(row.get("context_id"), "context_id")
    context = contexts.get(context_id)
    if context is None:
        raise ValueError(f"{row.get('id', 'unknown')}: unknown context_id {context_id!r}")
    if context["decision_stage"] != stage:
        raise ValueError(
            f"{row.get('id', 'unknown')}: context decision_stage does not match"
        )
    return context


def _index_unique(
    rows: Iterable[dict[str, Any]], field: str, label: str
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = _nonempty(row.get(field), field)
        if key in result:
            raise ValueError(f"duplicate {label} {field}: {key}")
        result[key] = row
    return result


def _require_fields(
    row: Mapping[str, Any], required: set[str], label: str
) -> None:
    missing = sorted(required - set(row))
    if missing:
        raise ValueError(f"{label}: missing required fields: {', '.join(missing)}")


def _decision(value: Any, field: str) -> str:
    decision = _nonempty(value, field)
    if decision not in DECISIONS:
        raise ValueError(f"{field} must be proceed, clarify, or block")
    return decision


def _decision_stage(value: Any) -> str:
    stage = _nonempty(value, "decision_stage")
    if stage not in STAGES:
        raise ValueError(f"unsupported decision_stage: {stage}")
    return stage


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()
