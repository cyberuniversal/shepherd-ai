"""Build a hash-bound, explicitly unreviewed manuscript review packet."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


PACKET_VERSION = "multiuav_external_review_packet_v1"
EXPECTED_AUDIT_STATUS = (
    "manuscript_internal_traceability_passed_final_package_pending"
)
TEXT_SUFFIXES = {".csv", ".json", ".md", ".txt"}


def build_external_review_packet(
    *,
    repository_root: Path,
    packet_path: Path,
    internal_audit_path: Path | None = None,
) -> dict[str, Any]:
    """Write a reviewer packet only when its internal audit is current and valid."""

    root = repository_root.resolve()
    packet_path = packet_path.resolve()
    internal_audit_path = (
        internal_audit_path
        or root
        / "outputs"
        / "evaluations"
        / "multiuav_manuscript_traceability_v1.json"
    ).resolve()
    paths = {
        "manuscript": root
        / "reports"
        / "multiuav_validation_placement_manuscript_v1.md",
        "internal_traceability_audit": internal_audit_path,
        "external_review_protocol": root
        / "docs"
        / "multiuav_external_review_protocol.md",
        "bibliography": root / "reports" / "week9_bibliography.md",
        "accuracy_figure_manifest": root
        / "outputs"
        / "evaluations"
        / "multiuav_accuracy_figures_v1"
        / "manifest.json",
        "resource_reporting_manifest": root
        / "outputs"
        / "evaluations"
        / "multiuav_resource_reporting_v1"
        / "manifest.json",
        "accuracy_contrast_table": root
        / "outputs"
        / "tables"
        / "multiuav_accuracy_registered_contrasts_v1.csv",
        "resource_contrast_table": root
        / "outputs"
        / "tables"
        / "multiuav_resource_contrasts_v1.csv",
        "accuracy_primary_figure": root
        / "reports"
        / "figures"
        / "multiuav_accuracy_primary_outcomes_v1.png",
        "accuracy_contrast_figure": root
        / "reports"
        / "figures"
        / "multiuav_accuracy_registered_contrasts_v1.png",
        "resource_primary_figure": root
        / "reports"
        / "figures"
        / "multiuav_resource_m3_minus_m1_v1.png",
        "resource_matched_figure": root
        / "reports"
        / "figures"
        / "multiuav_resource_m3_minus_m4_v1.png",
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "external review packet inputs missing: " + ", ".join(sorted(missing))
        )

    audit = _read_object(internal_audit_path)
    _validate_internal_audit(audit, manuscript_path=paths["manuscript"])

    bindings = {
        name: _file_record(root, path) for name, path in sorted(paths.items())
    }
    packet = _render_packet(
        manuscript=paths["manuscript"].read_text(encoding="utf-8-sig"),
        protocol=paths["external_review_protocol"].read_text(
            encoding="utf-8-sig"
        ),
        bindings=bindings,
    )
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_bytes(packet.encode("utf-8"))

    return {
        "schema_version": 1,
        "packet_version": PACKET_VERSION,
        "status": "external_review_packet_ready_review_not_received",
        "external_review_received": False,
        "reviewer_id": None,
        "review_artifact": None,
        "artifact_bindings": bindings,
        "packet": _file_record(root, packet_path),
        "packet_sha256": _sha256_file(packet_path),
        "source_code_sha256": {
            "multiuav_external_review.py": _sha256_file(Path(__file__))
        },
        "raw_model_outputs_accessed": False,
        "hidden_labels_accessed": False,
        "next_gate": "external_scientific_review_pending",
    }


def _validate_internal_audit(
    audit: Mapping[str, Any], *, manuscript_path: Path
) -> None:
    if (
        audit.get("valid") is not True
        or audit.get("status") != EXPECTED_AUDIT_STATUS
        or audit.get("failed_checks") != []
    ):
        raise ValueError("internal manuscript traceability audit has not passed")

    bindings = audit.get("artifact_bindings")
    if not isinstance(bindings, Mapping):
        raise ValueError("internal manuscript traceability bindings are missing")
    manuscript_binding = bindings.get("manuscript")
    if not isinstance(manuscript_binding, Mapping):
        raise ValueError("internal manuscript traceability binding is missing")
    if manuscript_binding.get("sha256") != _sha256_file(manuscript_path):
        raise ValueError("internal manuscript traceability audit is stale")


def _render_packet(
    *, manuscript: str, protocol: str, bindings: Mapping[str, Mapping[str, Any]]
) -> str:
    rows = ["| Artifact | Path | SHA-256 |", "|---|---|---|"]
    rows.extend(
        f"| `{name}` | `{record['path']}` | `{record['sha256']}` |"
        for name, record in bindings.items()
    )
    protocol_body = protocol.split("\n", maxsplit=1)[-1].strip()
    manuscript_body = manuscript.strip()
    return (
        "# MultiUAV Manuscript External Review Packet\n\n"
        "**Status:** ready for external review; no external review has been "
        "received.\n\n"
        "Do not mark this packet as reviewed, approved, or externally validated "
        "until a real reviewer returns a response that satisfies the protocol.\n\n"
        "The hashes below bind this packet to the exact manuscript and aggregate "
        "evidence artifacts. A changed manuscript requires a newly generated "
        "packet and a new review round. Text hashes use UTF-8 bytes with a "
        "single LF newline convention; binary hashes use raw bytes.\n\n"
        "## Artifact bindings\n\n"
        + "\n".join(rows)
        + "\n\n## Review protocol\n\n"
        + protocol_body
        + "\n\n## Reviewer response fields\n\n"
        "- Reviewer pseudonym:\n"
        "- Relevant expertise:\n"
        "- Conflict-of-interest declaration:\n"
        "- Overall assessment:\n"
        "- Numbered findings with severity, section, and rationale:\n"
        "- Required corrections:\n"
        "- Optional improvements:\n"
        "- Abstract and conclusion match the results (yes/no, with explanation):\n"
        "- Review date:\n\n"
        "## Manuscript under review\n\n"
        + manuscript_body
        + "\n"
    )


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid internal traceability audit: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError("internal manuscript traceability audit must be an object")
    return value


def _file_record(root: Path, path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    try:
        label = resolved.relative_to(root).as_posix()
    except ValueError:
        label = resolved.as_posix()
    data, hash_basis = _binding_bytes(resolved)
    return {
        "path": label,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "hash_basis": hash_basis,
    }


def _binding_bytes(path: Path) -> tuple[bytes, str]:
    if path.suffix.lower() in TEXT_SUFFIXES:
        text = path.read_text(encoding="utf-8-sig")
        return text.encode("utf-8"), "utf8_lf_normalized"
    return path.read_bytes(), "raw_bytes"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
