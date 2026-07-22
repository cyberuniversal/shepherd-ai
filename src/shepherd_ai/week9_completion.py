"""Completion audit for the Week 9 research-paper draft milestone."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Mapping


REQUIRED_SECTIONS = (
    "## Abstract",
    "## 1. Introduction",
    "## 2. Motivation",
    "## 3. Problem Statement",
    "## 4. Objectives",
    "## 5. Related Work",
    "## 6. Proposed Method",
    "## 7. System Architecture",
    "## 8. Methodology",
    "## References",
)
REQUIRED_REFERENCES = tuple(f"L{index}" for index in range(1, 16))


@dataclass(frozen=True)
class CompletionGate:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class Week9CompletionAudit:
    gates: tuple[CompletionGate, ...]
    completion_allowed: bool
    decision: str
    blockers: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gates": [gate.to_dict() for gate in self.gates],
            "gates_passed": all(gate.passed for gate in self.gates),
            "completion_allowed": self.completion_allowed,
            "decision": self.decision,
            "blockers": list(self.blockers),
        }


def build_week9_completion_audit(
    *,
    paper_text: str,
    bibliography_text: str,
    notebook_text: str,
    evidence: Mapping[str, Any],
    artifact_status: Mapping[str, bool],
) -> Week9CompletionAudit:
    sections = [section for section in REQUIRED_SECTIONS if section in paper_text]
    bibliography_refs = set(re.findall(r"\*\*\[(L\d+)\]\*\*", bibliography_text))
    paper_refs = _extract_reference_ids(paper_text)
    expected_refs = set(REQUIRED_REFERENCES)
    claim_limits = evidence.get("claim_limits", {})
    metric_rows = evidence.get("metric_rows", [])
    metrics = {row.get("metric") for row in metric_rows if isinstance(row, Mapping)}
    gates = (
        _gate(
            "all_roadmap_draft_sections_present",
            len(sections) == len(REQUIRED_SECTIONS),
            f"sections={len(sections)}/{len(REQUIRED_SECTIONS)}",
        ),
        _gate(
            "organized_bibliography_covers_review",
            bibliography_refs == expected_refs,
            f"references={len(bibliography_refs)}/{len(expected_refs)}",
        ),
        _gate(
            "paper_citations_resolve_to_bibliography",
            paper_refs == expected_refs,
            f"cited={sorted(paper_refs)}, undefined={sorted(paper_refs - bibliography_refs)}",
        ),
        _gate(
            "five_roadmap_metrics_traceable",
            metrics
            == {
                "intent_extraction_accuracy",
                "grounding_accuracy",
                "scheduling_quality",
                "detection_performance",
                "overall_execution_time",
            },
            f"metrics={sorted(str(metric) for metric in metrics)}",
        ),
        _gate(
            "negative_vision_result_preserved",
            "0.02356" in paper_text and ("weak" in paper_text.lower() or "negative" in paper_text.lower()),
            "paper includes the measured weak mission-vision result",
        ),
        _gate(
            "claim_limits_preserved",
            claim_limits.get("physical_flight_claimed") is False
            and claim_limits.get("safety_guarantee_claimed") is False
            and claim_limits.get("novelty_claimed") is False
            and "not a final paper or accepted novelty claim" in paper_text.lower(),
            f"claim_limits={dict(claim_limits)}",
        ),
        _gate(
            "paper_artifacts_present",
            bool(artifact_status) and all(artifact_status.values()),
            f"artifacts={dict(sorted(artifact_status.items()))}",
        ),
        _gate(
            "notebook_regenerates_artifacts",
            "scripts/build_week9_paper_artifacts.py" in notebook_text
            and "load_week9_paper_evidence" in notebook_text,
            "Notebook 9 validates and regenerates registered paper evidence",
        ),
    )
    blockers = tuple(gate.name for gate in gates if not gate.passed)
    allowed = not blockers
    return Week9CompletionAudit(
        gates=gates,
        completion_allowed=allowed,
        decision=(
            "week9_paper_draft_complete_for_advancement_to_week10"
            if allowed
            else "remain_on_week9_until_paper_draft_evidence_is_complete"
        ),
        blockers=blockers,
    )


def render_week9_completion_markdown(audit: Week9CompletionAudit) -> str:
    payload = audit.to_dict()
    lines = [
        "# Week 9 Completion Gate Audit",
        "",
        "This audit checks roadmap draft completeness and evidence traceability, not publication readiness.",
        "",
        "## Decision",
        "",
        f"- Completion allowed: `{str(payload['completion_allowed']).lower()}`",
        f"- Decision: `{payload['decision']}`",
        "",
        "## Gates",
        "",
    ]
    lines.extend(
        f"- `{gate['name']}`: `{str(gate['passed']).lower()}`; {gate['detail']}"
        for gate in payload["gates"]
    )
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- `{blocker}`" for blocker in payload["blockers"])
    if not payload["blockers"]:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def _gate(name: str, passed: bool, detail: str) -> CompletionGate:
    return CompletionGate(name=name, passed=bool(passed), detail=detail)


def _extract_reference_ids(text: str) -> set[str]:
    references: set[str] = set()
    for bracket in re.findall(r"\[([^\]]+)\]", text):
        for match in re.finditer(r"L(\d+)(?:-L?(\d+))?", bracket):
            start = int(match.group(1))
            end = int(match.group(2) or start)
            if end < start:
                start, end = end, start
            references.update(f"L{index}" for index in range(start, end + 1))
    return references
