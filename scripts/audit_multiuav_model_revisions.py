"""Audit immutable Qwen revisions without downloading model weights."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Mapping
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_model_revisions import (  # noqa: E402
    build_model_revision_audit,
)
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--skip-remote-verification",
        action="store_true",
        help="Validate the local registry only; intended for offline smoke tests.",
    )
    args = parser.parse_args()

    audit = build_model_revision_audit(
        fetch_json=None if args.skip_remote_verification else _fetch_json,
        resolved_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    module_path = (
        ROOT / "src" / "shepherd_ai" / "multiuav_model_revisions.py"
    )
    script_path = ROOT / "scripts" / "audit_multiuav_model_revisions.py"
    audit["source_code_sha256"] = {
        "multiuav_model_revisions.py": sha256_file(module_path),
        "audit_multiuav_model_revisions.py": sha256_file(script_path),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    if not audit["valid"]:
        raise SystemExit(1)


def _fetch_json(url: str) -> Mapping[str, Any]:
    request = Request(
        url,
        headers={"User-Agent": "shepherd-ai-model-revision-audit/1"},
    )
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if not isinstance(payload, Mapping):
        raise ValueError("Hugging Face response root is not an object")
    return payload


if __name__ == "__main__":
    main()
