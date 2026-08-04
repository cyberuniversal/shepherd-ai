"""Frozen planning-validity scope for the MultiUAV study."""

from __future__ import annotations

from typing import Any


EXECUTION_SCOPE_VERSION = "multiuav_static_fidelity_v1"


def execution_scope_contract() -> dict[str, Any]:
    """Return the registered static-only primary evaluation boundary."""

    return {
        "schema_version": 1,
        "scope_version": EXECUTION_SCOPE_VERSION,
        "primary_scope": "static_plan_fidelity",
        "official_server_submission_in_primary_scope": False,
        "live_simulator_execution_in_primary_scope": False,
        "primary_fidelity_metrics": [
            "json_schema_validity",
            "endpoint_validity",
            "parameter_grounding",
            "official_command_fidelity",
        ],
        "permitted_claim": (
            "static API, parameter, and official-command fidelity"
        ),
        "prohibited_claims": [
            "live mission success",
            "simulator mission success",
            "physical UAV mission success",
        ],
        "upgrade_rule": (
            "execution claims require separate official-server submission, "
            "recorded server checks, and a new frozen scope version"
        ),
    }
