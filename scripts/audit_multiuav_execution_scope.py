"""Freeze the MultiUAV primary evaluation as static plan fidelity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_execution_scope import (  # noqa: E402
    execution_scope_contract,
)
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = {
        **execution_scope_contract(),
        "valid": True,
        "official_server_invoked_by_this_audit": False,
        "model_invoked_by_this_audit": False,
        "study_cases_evaluated": False,
        "source_code_sha256": {
            "multiuav_execution_scope.py": sha256_file(
                ROOT / "src" / "shepherd_ai" / "multiuav_execution_scope.py"
            ),
            "audit_multiuav_execution_scope.py": sha256_file(
                ROOT / "scripts" / "audit_multiuav_execution_scope.py"
            ),
        },
        "claim_status": "static_fidelity_scope_frozen_no_live_execution",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
