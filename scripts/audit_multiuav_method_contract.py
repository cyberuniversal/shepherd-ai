"""Freeze and audit MultiUAV method call budgets and strict output contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_methods import (  # noqa: E402
    METHOD_SPECS,
    validate_method_specs,
)
from shepherd_ai.multiuav_plan_contract import (  # noqa: E402
    API_CALL_FIELDS,
    DECISIONS,
    OUTPUT_FIELDS,
)
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    methods_path = ROOT / "src" / "shepherd_ai" / "multiuav_methods.py"
    contract_path = ROOT / "src" / "shepherd_ai" / "multiuav_plan_contract.py"
    validation = validate_method_specs()
    result = {
        "schema_version": 1,
        "valid": True,
        "methods": [spec.to_dict() for spec in METHOD_SPECS],
        "method_validation": validation,
        "strict_output_contract": {
            "decisions": sorted(DECISIONS),
            "output_fields": sorted(OUTPUT_FIELDS),
            "api_call_fields": sorted(API_CALL_FIELDS),
            "execute_requires_nonempty_plan": True,
            "clarify_requires_nonempty_question": True,
            "nonexecute_requires_empty_plan": True,
            "malformed_output_status": "PARSE_ERROR",
            "silent_repair_allowed": False,
            "api_plan_shape": "MultiUAV related_apis endpoint_parameters",
        },
        "source_code_sha256": {
            "multiuav_methods.py": sha256_file(methods_path),
            "multiuav_plan_contract.py": sha256_file(contract_path),
        },
        "claim_status": (
            "call_budget_and_structural_contract_frozen_"
            "recursive_grounding_not_implemented"
        ),
        "limitations": [
            (
                "M3 and M4 are matched on model-call count only; tokens, "
                "latency, memory, and energy must be measured and reported."
            ),
            (
                "The structural parser does not establish endpoint validity, "
                "parameter grounding, plan fidelity, or mission success."
            ),
            "No revised-study model was loaded or invoked.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
