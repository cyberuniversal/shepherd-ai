"""Integrity and schema auditing for the pinned MultiUAV-Plat benchmark."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from zipfile import ZipFile


EXPECTED_ARCHIVE_SHA256 = (
    "b5040097d2bfdd44600f3bf486fdb43ee3eb1247fec9c67900b5fcda6feb94a3"
)
EXPECTED_ARCHIVE_SIZE = 11_709_646
EXPECTED_SESSION_COUNT = 75
EXPECTED_TASK_COUNT = 1_500
EXPECTED_CHECK_COUNT = 9_396
EXPECTED_IMAGE_COUNT = 75
EXPECTED_ALIAS_COUNT = 5_794

SESSION_REQUIRED_FIELDS = {
    "id",
    "name",
    "task_type",
    "drones",
    "targets",
    "obstacles",
    "environment",
    "tasks",
}
TASK_REQUIRED_FIELDS = {
    "id",
    "name",
    "content",
    "content_aliases",
    "difficulty",
    "related_apis",
    "execution_check_apis",
    "commands",
    "is_done",
    "is_passed",
}

# These fields are colocated with task text upstream but disclose intended
# actions, gold checks, or outcome state. Dataset builders must use a positive
# allowlist and must never expose these fields to evaluated models.
PRIVILEGED_TASK_FIELDS = {
    "related_apis",
    "execution_check_apis",
    "commands",
    "is_done",
    "is_passed",
}
PRIVILEGED_SESSION_FIELDS = {"history", "statistics"}
SOURCE_TEXT_FIELDS = {"id", "content", "content_aliases"}

_DIFFICULTY_PATTERN = re.compile(
    r"_(Easy|Intermediate|Moderate|Hard|Extreme)_", re.IGNORECASE
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_instruction(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def audit_benchmark_archive(
    archive: Path,
    *,
    enforce_pinned_artifact: bool = True,
) -> dict[str, Any]:
    """Audit a benchmark ZIP without extracting or modifying it."""

    if not archive.is_file():
        raise ValueError(f"benchmark archive does not exist: {archive}")

    archive_sha256 = sha256_file(archive)
    archive_size = archive.stat().st_size
    if enforce_pinned_artifact:
        if archive_sha256 != EXPECTED_ARCHIVE_SHA256:
            raise ValueError(
                "benchmark archive SHA-256 mismatch: "
                f"expected {EXPECTED_ARCHIVE_SHA256}, got {archive_sha256}"
            )
        if archive_size != EXPECTED_ARCHIVE_SIZE:
            raise ValueError(
                "benchmark archive size mismatch: "
                f"expected {EXPECTED_ARCHIVE_SIZE}, got {archive_size}"
            )

    with ZipFile(archive) as bundle:
        members = [name for name in bundle.namelist() if not name.endswith("/")]
        json_members = sorted(name for name in members if name.lower().endswith(".json"))
        image_members = sorted(name for name in members if name.lower().endswith(".jpg"))
        unexpected_members = sorted(
            name
            for name in members
            if not name.lower().endswith((".json", ".jpg"))
        )
        _validate_paired_members(json_members, image_members)

        session_ids: set[str] = set()
        task_ids: set[str] = set()
        canonical_texts: list[str] = []
        alias_texts: list[str] = []
        scenario_counts: Counter[str] = Counter()
        session_difficulty_counts: Counter[str] = Counter()
        task_difficulty_counts: Counter[str] = Counter()
        alias_count_distribution: Counter[int] = Counter()
        check_count = 0

        for member in json_members:
            try:
                session = json.loads(bundle.read(member))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError(f"{member}: invalid JSON: {error}") from error
            _require_object(session, f"{member}: session")
            _require_fields(session, SESSION_REQUIRED_FIELDS, f"{member}: session")

            session_id = _nonempty_text(session["id"], f"{member}: session id")
            if session_id in session_ids:
                raise ValueError(f"{member}: duplicate session id {session_id!r}")
            session_ids.add(session_id)

            task_type = _nonempty_text(
                session["task_type"], f"{member}: task_type"
            )
            scenario_counts[task_type] += 1
            difficulty_match = _DIFFICULTY_PATTERN.search(Path(member).name)
            if difficulty_match is None:
                raise ValueError(f"{member}: difficulty is absent from filename")
            session_difficulty_counts[difficulty_match.group(1).lower()] += 1

            tasks = session["tasks"]
            if not isinstance(tasks, list) or not tasks:
                raise ValueError(f"{member}: tasks must be a non-empty list")
            for task_index, task in enumerate(tasks):
                label = f"{member}: task {task_index}"
                _require_object(task, label)
                _require_fields(task, TASK_REQUIRED_FIELDS, label)
                task_id = _nonempty_text(task["id"], f"{label} id")
                if task_id in task_ids:
                    raise ValueError(f"{label}: duplicate task id {task_id!r}")
                task_ids.add(task_id)

                content = _nonempty_text(task["content"], f"{label} content")
                aliases = task["content_aliases"]
                if not isinstance(aliases, list) or not aliases:
                    raise ValueError(
                        f"{label}: content_aliases must be a non-empty list"
                    )
                for alias_index, alias in enumerate(aliases):
                    alias_texts.append(
                        _nonempty_text(alias, f"{label} alias {alias_index}")
                    )
                canonical_texts.append(content)
                alias_count_distribution[len(aliases)] += 1
                task_difficulty_counts[
                    _nonempty_text(task["difficulty"], f"{label} difficulty")
                ] += 1

                if not isinstance(task["related_apis"], list):
                    raise ValueError(f"{label}: related_apis must be a list")
                if not isinstance(task["commands"], list):
                    raise ValueError(f"{label}: commands must be a list")
                check_count += _count_validation_leaves(
                    task["execution_check_apis"],
                    label=f"{label} execution_check_apis",
                )

    canonical_normalized = [normalize_instruction(text) for text in canonical_texts]
    alias_normalized = [normalize_instruction(text) for text in alias_texts]
    combined_normalized = canonical_normalized + alias_normalized
    summary = {
        "archive": {
            "sha256": archive_sha256,
            "size_bytes": archive_size,
            "member_count": len(members),
            "unexpected_members": unexpected_members,
        },
        "counts": {
            "sessions": len(session_ids),
            "tasks": len(task_ids),
            "validation_check_leaves": check_count,
            "images": len(image_members),
            "official_aliases": len(alias_texts),
        },
        "distributions": {
            "scenario_sessions": dict(sorted(scenario_counts.items())),
            "session_difficulties": dict(sorted(session_difficulty_counts.items())),
            "task_difficulties": dict(sorted(task_difficulty_counts.items())),
            "aliases_per_task": {
                str(key): value
                for key, value in sorted(alias_count_distribution.items())
            },
        },
        "instruction_uniqueness": {
            "canonical_normalized_unique": len(set(canonical_normalized)),
            "canonical_normalized_duplicates": (
                len(canonical_normalized) - len(set(canonical_normalized))
            ),
            "alias_normalized_unique": len(set(alias_normalized)),
            "alias_normalized_duplicates": len(alias_normalized) - len(set(alias_normalized)),
            "canonical_and_alias_normalized_duplicates": (
                len(combined_normalized) - len(set(combined_normalized))
            ),
        },
        "field_policy": {
            "source_text_allowlist": sorted(SOURCE_TEXT_FIELDS),
            "privileged_task_fields": sorted(PRIVILEGED_TASK_FIELDS),
            "privileged_session_fields": sorted(PRIVILEGED_SESSION_FIELDS),
        },
    }
    if enforce_pinned_artifact:
        _validate_expected_counts(summary["counts"])
    return summary


def _validate_paired_members(
    json_members: list[str],
    image_members: list[str],
) -> None:
    json_stems = {str(Path(name).with_suffix("")) for name in json_members}
    image_stems = {str(Path(name).with_suffix("")) for name in image_members}
    missing_images = sorted(json_stems - image_stems)
    missing_json = sorted(image_stems - json_stems)
    if missing_images or missing_json:
        raise ValueError(
            "benchmark JSON/JPG members are not paired; "
            f"missing_images={missing_images}, missing_json={missing_json}"
        )


def _count_validation_leaves(node: Any, *, label: str) -> int:
    if not isinstance(node, dict):
        raise ValueError(f"{label}: check node must be an object")
    if "endpoint" in node:
        _nonempty_text(node["endpoint"], f"{label} endpoint")
        if not isinstance(node.get("parameters"), dict):
            raise ValueError(f"{label}: check parameters must be an object")
        return 1
    logic = node.get("logic")
    checks = node.get("checks")
    if logic not in {"and", "or", "not"}:
        raise ValueError(f"{label}: check group has invalid logic {logic!r}")
    if not isinstance(checks, list) or not checks:
        raise ValueError(f"{label}: check group must contain checks")
    return sum(
        _count_validation_leaves(child, label=f"{label}.checks[{index}]")
        for index, child in enumerate(checks)
    )


def _validate_expected_counts(counts: dict[str, int]) -> None:
    expected = {
        "sessions": EXPECTED_SESSION_COUNT,
        "tasks": EXPECTED_TASK_COUNT,
        "validation_check_leaves": EXPECTED_CHECK_COUNT,
        "images": EXPECTED_IMAGE_COUNT,
        "official_aliases": EXPECTED_ALIAS_COUNT,
    }
    mismatches = {
        key: {"expected": value, "actual": counts.get(key)}
        for key, value in expected.items()
        if counts.get(key) != value
    }
    if mismatches:
        raise ValueError(f"pinned benchmark count mismatch: {mismatches}")


def _require_object(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")


def _require_fields(value: dict[str, Any], fields: set[str], label: str) -> None:
    missing = sorted(fields - value.keys())
    if missing:
        raise ValueError(f"{label} missing required fields: {missing}")


def _nonempty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()
