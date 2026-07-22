"""Traceable paper artifacts derived from registered Shepherd-AI evidence."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any, Mapping


REQUIRED_METRICS = (
    "intent_extraction_accuracy",
    "grounding_accuracy",
    "scheduling_quality",
    "detection_performance",
    "overall_execution_time",
)


def load_week9_paper_evidence(
    root: Path,
    *,
    evaluation_path: Path | None = None,
    audit_path: Path | None = None,
) -> dict[str, Any]:
    """Load and validate the evidence allowed to support the Week 9 draft."""

    evaluation_path = evaluation_path or root / "outputs/evaluations/week8_end_to_end_evaluation.json"
    audit_path = audit_path or root / "outputs/evaluations/week8_completion_gate_audit.json"
    evaluation = _read_object(evaluation_path)
    audit = _read_object(audit_path)

    if audit.get("completion_allowed") is not True or audit.get("blockers") != []:
        raise ValueError("Week 8 completion audit does not permit paper drafting")
    for key in ("physical_flight_claimed", "safety_guarantee_claimed", "novelty_claimed"):
        if evaluation.get(key) is not False:
            raise ValueError(f"claim-limit flag must be false: {key}")

    metrics = evaluation.get("metrics")
    if not isinstance(metrics, Mapping):
        raise ValueError("evaluation metrics must be an object")

    metric_rows: list[dict[str, Any]] = []
    for name in REQUIRED_METRICS:
        record = metrics.get(name)
        if not isinstance(record, Mapping):
            raise ValueError(f"missing roadmap metric: {name}")
        value = _finite_number(record.get("value"), f"{name}.value")
        denominator = int(record.get("denominator", 0))
        if denominator < 1:
            raise ValueError(f"metric denominator must be positive: {name}")
        source = str(record.get("source_artifact") or evaluation_path.relative_to(root)).replace("\\", "/")
        source_path = root / source
        if not source_path.is_file():
            raise FileNotFoundError(f"metric source artifact does not exist: {source}")
        metric_rows.append(
            {
                "metric": name,
                "value": value,
                "denominator": denominator,
                "unit": str(record.get("unit", "ratio")),
                "definition": str(record.get("definition", "not stated")),
                "source_artifact": source,
            }
        )

    timings = metrics["overall_execution_time"].get("stage_timings")
    if not isinstance(timings, Mapping) or not timings:
        raise ValueError("overall execution time must include stage timings")
    runtime_rows = [
        {"stage": stage, "seconds": _finite_number(seconds, f"stage_timings.{stage}")}
        for stage, seconds in timings.items()
    ]

    return {
        "evidence_role": "week9_paper_draft_source_manifest",
        "week8_decision": audit.get("decision"),
        "evaluation_status": evaluation.get("status"),
        "evaluation_generated_at_utc": evaluation.get("generated_at_utc"),
        "source_files": [
            _file_record(root, evaluation_path),
            _file_record(root, audit_path),
        ],
        "metric_rows": metric_rows,
        "runtime_rows": runtime_rows,
        "limitations": list(evaluation.get("limitations", [])),
        "claim_limits": {
            "physical_flight_claimed": False,
            "safety_guarantee_claimed": False,
            "novelty_claimed": False,
        },
    }


def render_csv(rows: list[Mapping[str, Any]], fieldnames: tuple[str, ...]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def render_traceability_markdown(evidence: Mapping[str, Any]) -> str:
    lines = [
        "# Week 9 Paper Evidence Traceability",
        "",
        f"Week 8 decision: `{evidence['week8_decision']}`.",
        "",
        "| Metric | Value | Denominator | Unit | Source |",
        "|---|---:|---:|---|---|",
    ]
    for row in evidence["metric_rows"]:
        lines.append(
            f"| `{row['metric']}` | {row['value']:.8g} | {row['denominator']} | "
            f"{row['unit']} | `{row['source_artifact']}` |"
        )
    lines.extend(["", "## Claim Limits", ""])
    for name, value in evidence["claim_limits"].items():
        lines.append(f"- `{name}`: `{str(value).lower()}`")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in evidence["limitations"])
    return "\n".join(lines) + "\n"


def system_architecture_mermaid() -> str:
    return """flowchart LR
    A[Voice or typed command] --> B[Whisper ASR]
    A --> C[Typed input]
    B --> D[Bounded intent extraction]
    C --> D
    D --> E[Map grounding and clarification]
    E --> F[Task-sequence planner]
    F --> G[Multi-drone scheduler]
    G --> H[Deterministic safety gate]
    H -->|approved| I[Software mission simulator]
    H -->|blocked| J[Operator feedback]
    I --> K[Registered mission imagery]
    K --> L[Frozen vision inference]
    I --> M[Telemetry and supervision]
    L --> N[Mission report and evaluation]
    M --> N
"""


def evaluation_workflow_mermaid() -> str:
    return """flowchart TD
    A[Raw registered inputs] --> B[Per-module raw predictions]
    B --> C[Deterministic evaluators]
    C --> D[Five roadmap metrics]
    D --> E[Completion-gate audit]
    E -->|pass| F[Week 9 evidence manifest]
    E -->|fail| G[Preserved blockers and negative result]
    F --> H[Generated tables and runtime figure]
    H --> I[Paper draft]
"""


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"expected numeric value: {label}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"expected finite value: {label}")
    return result


def _file_record(root: Path, path: Path) -> dict[str, str]:
    return {
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
