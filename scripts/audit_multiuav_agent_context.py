"""Audit the AGENT-visible projection over the pinned MultiUAV archive."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_context import (  # noqa: E402
    AGENT_OBSERVATION_ENDPOINTS,
    CONTEXT_SCHEMA_VERSION,
    privileged_noninterference_check,
    project_agent_visible_context,
)
from shepherd_ai.multiuav_source import (  # noqa: E402
    EXPECTED_ARCHIVE_SHA256,
    EXPECTED_SESSION_COUNT,
    EXPECTED_TASK_COUNT,
    sha256_file,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        type=Path,
        default=ROOT / "external" / "MultiUAV-Plat" / "benchmark" / "benchmark.zip",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    archive_hash = sha256_file(args.archive)
    if archive_hash != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("benchmark archive does not match the pinned SHA-256")

    session_count = 0
    task_count = 0
    noninterference_count = 0
    context_hashes: set[str] = set()
    with ZipFile(args.archive) as bundle:
        members = sorted(
            name for name in bundle.namelist() if name.lower().endswith(".json")
        )
        for member in members:
            session_count += 1
            session = json.loads(bundle.read(member))
            for task in session["tasks"]:
                task_count += 1
                context = project_agent_visible_context(
                    session,
                    task_id=task["id"],
                    instruction=task["content"],
                )
                context_hashes.add(_sha256_json(context))
                if privileged_noninterference_check(
                    session,
                    task_id=task["id"],
                    instruction=task["content"],
                ):
                    noninterference_count += 1

    if session_count != EXPECTED_SESSION_COUNT or task_count != EXPECTED_TASK_COUNT:
        raise ValueError("context audit counts do not match the pinned benchmark")
    if noninterference_count != task_count:
        raise ValueError("privileged source values affect at least one context")

    result = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_archive_sha256": archive_hash,
        "context_schema_version": CONTEXT_SCHEMA_VERSION,
        "summary": {
            "sessions_audited": session_count,
            "tasks_audited": task_count,
            "privileged_noninterference_passes": noninterference_count,
            "unique_context_hashes": len(context_hashes),
            "privileged_field_leaks": 0,
        },
        "agent_role_contract": {
            "global_targets_visible": False,
            "global_obstacles_visible": False,
            "allowed_observation_endpoints": list(AGENT_OBSERVATION_ENDPOINTS),
        },
        "claim_status": "agent_visible_context_projection_audited_only",
        "limitations": [
            "Canonical instructions were used only to audit projection structure.",
            "No five-variant intervention contexts were generated.",
            "No prompt, model inference, task execution, or evaluation occurred.",
            "Local target and obstacle observations remain runtime evidence and are not pre-exposed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))


def _sha256_json(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


if __name__ == "__main__":
    main()
