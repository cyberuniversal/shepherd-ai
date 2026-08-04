"""Freeze MultiUAV prompt, runner, and checkpoint contract metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_checkpoints import (  # noqa: E402
    CHECKPOINT_SCHEMA_VERSION,
)
from shepherd_ai.multiuav_context import PRIVILEGED_SOURCE_FIELDS  # noqa: E402
from shepherd_ai.multiuav_interventions import (  # noqa: E402
    materialize_case_context,
)
from shepherd_ai.multiuav_methods import METHOD_SPECS  # noqa: E402
from shepherd_ai.multiuav_prompts import (  # noqa: E402
    PROMPT_CONTRACT_VERSION,
    build_first_call_request,
    prompt_template_audit,
)
from shepherd_ai.multiuav_runner import RUNNABLE_CASE_STATUSES  # noqa: E402
from shepherd_ai.multiuav_source import sha256_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    qwen_artifacts = {
        scale: {
            "cache_path": ROOT
            / "datasets"
            / "multiuav_plat"
            / f"qwen25_{scale}_cache_audit_v1.json",
            "smoke_path": ROOT
            / "datasets"
            / "multiuav_plat"
            / f"qwen25_{scale}_load_smoke_v1.json",
        }
        for scale in ("3b", "7b")
    }
    for paths in qwen_artifacts.values():
        paths["cache"] = json.loads(
            paths["cache_path"].read_text(encoding="utf-8")
        )
        paths["smoke"] = json.loads(
            paths["smoke_path"].read_text(encoding="utf-8")
        )

    source_names = (
        "multiuav_prompts.py",
        "multiuav_ledger_contract.py",
        "multiuav_runner.py",
        "multiuav_checkpoints.py",
        "multiuav_experiment.py",
        "multiuav_resources.py",
        "multiuav_resource_schedule.py",
        "multiuav_publication.py",
        "multiuav_offline_runtime.py",
        "multiuav_qwen_backend.py",
    )
    prompt_leakage = _audit_pilot_first_prompts()
    result = {
        "schema_version": 1,
        "valid": prompt_leakage["valid"],
        "prompt_contract": prompt_template_audit(),
        "pilot_prompt_leakage_audit": prompt_leakage,
        "runner_contract": {
            "method_call_counts": {
                spec.method_id: spec.model_call_count for spec in METHOD_SPECS
            },
            "m3_second_call_always_required": True,
            "raw_outputs_retained": True,
            "backend_errors_retained_as_rows": True,
            "parse_errors_retained": True,
            "deterministic_postplan_methods": [
                spec.method_id
                for spec in METHOD_SPECS
                if spec.deterministic_postplan_gate
            ],
            "runnable_case_statuses": sorted(RUNNABLE_CASE_STATUSES),
            "pending_human_review_allowed": False,
            "provider_independent_backend_protocol": True,
            "qwen_backend_implemented": True,
            "qwen_local_files_only_required": True,
            "qwen_non_loopback_socket_guard_implemented": True,
            "qwen_weights_loaded_by_this_audit": False,
            "accuracy_execution_cli_implemented": True,
            "accuracy_preflight_validates_commit_data_cache_and_counts": True,
            "durable_row_progress_reporting": True,
            "resource_measurement_unit": "complete_method_case",
            "resource_monitor_required_for_resource_runs": True,
            "resource_monitor_forbidden_for_accuracy_runs": True,
            **{
                f"qwen_{scale}_synthetic_load_smoke_registered": (
                    paths["smoke"].get("smoke_status") == "passed"
                    and paths["smoke"].get("model_invoked") is True
                    and paths["smoke"].get("study_cases_evaluated") is False
                )
                for scale, paths in qwen_artifacts.items()
            },
        },
        "checkpoint_contract": {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "row_written_after_each_method_case": True,
            "config_hash_on_every_row": True,
            "incompatible_resume_rejected": True,
            "duplicate_result_key_rejected": True,
            "matrix_completeness_check": True,
            "durable_flush_and_fsync": True,
            "periodic_compact_zip_supported": True,
            "compact_zip_contents": [
                "manifest.json",
                "results.jsonl",
                "run_config.json",
            ],
            "final_publication_package_implemented": False,
            "resource_repetition_bound_in_config_hash": True,
            "hardware_protocol_hash_bound_in_config_hash": True,
            "resource_condition_order_bound_in_config_hash": True,
            "resource_schedule_hash_bound_in_config_hash": True,
            "resource_measurement_retained_per_row": True,
        },
        "publication_accuracy_gate": {
            "accuracy_run_only": True,
            "approved_evaluation_cases_only": True,
            "complete_matrix_required": True,
            "synthetic_and_resource_rows_rejected": True,
            "parse_errors_retained": True,
            "study_rows_scored_by_this_audit": False,
        },
        "prompt_contract_version": PROMPT_CONTRACT_VERSION,
        "source_code_sha256": {
            **{
                name: sha256_file(ROOT / "src" / "shepherd_ai" / name)
                for name in source_names
            },
            "audit_multiuav_runner_contract.py": sha256_file(
                ROOT / "scripts" / "audit_multiuav_runner_contract.py"
            ),
            "run_multiuav_accuracy.py": sha256_file(
                ROOT / "scripts" / "run_multiuav_accuracy.py"
            ),
        },
        "registered_qwen_smokes": {
            scale: {
                "cache_audit_sha256": sha256_file(paths["cache_path"]),
                "load_smoke_sha256": sha256_file(paths["smoke_path"]),
                "model_id": paths["cache"].get("model_id"),
                "revision": paths["cache"].get("revision"),
                "weights_cached": paths["cache"].get("weights_cached"),
                "weights_loaded": paths["smoke"].get("weights_loaded"),
                "model_invoked": paths["smoke"].get("model_invoked"),
                "study_cases_evaluated": paths["smoke"].get(
                    "study_cases_evaluated"
                ),
                "smoke_status": paths["smoke"].get("smoke_status"),
            }
            for scale, paths in qwen_artifacts.items()
        },
        "model_invoked_by_this_audit": False,
        "weights_loaded_by_this_audit": False,
        "claim_status": (
            "prompt_runner_checkpoint_accuracy_cli_and_local_qwen_backend_implemented_"
            "qwen3b_and_qwen7b_synthetic_load_smokes_registered_"
            "no_study_inference"
        ),
        "limitations": [
            (
                "The pinned Qwen 3B and 7B checkpoints were loaded and invoked "
                "only in separately registered synthetic smokes; this contract "
                "audit itself does not load weights or invoke a model."
            ),
            (
                "The M3 pre-plan gate checks ledger structure, visible source "
                "paths, and internal decision consistency; it does not prove "
                "semantic correctness."
            ),
            (
                "The compact checkpoint ZIP is not the final publication "
                "package with summaries, figures, failure examples, and full "
                "runtime metadata."
            ),
            (
                "No unreviewed pilot case is eligible for model execution "
                "under the runner contract."
            ),
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["valid"]:
        raise SystemExit(1)


def _audit_pilot_first_prompts() -> dict[str, Any]:
    pilot_path = (
        ROOT
        / "datasets"
        / "multiuav_plat"
        / "intervention_pilot_v2.json"
    )
    pilot = json.loads(pilot_path.read_text(encoding="utf-8"))
    methods = tuple(spec.method_id for spec in METHOD_SPECS)
    prompt_count = 0
    errors: list[str] = []
    for cluster in pilot["clusters"]:
        for case in cluster["cases"]:
            context = materialize_case_context(cluster, case)
            for method_id in methods:
                request = build_first_call_request(method_id, context)
                payload = json.loads(request.messages[1].content)
                prompt_count += 1
                if payload.get("AGENT_CONTEXT") != context:
                    errors.append(
                        f"{case['case_id']}:{method_id}: context changed"
                    )
                leaked = _find_keys(payload, PRIVILEGED_SOURCE_FIELDS)
                if leaked:
                    errors.append(
                        f"{case['case_id']}:{method_id}: leaked {sorted(leaked)}"
                    )
                if "proposed_decision" in payload or "label_status" in payload:
                    errors.append(
                        f"{case['case_id']}:{method_id}: label field leaked"
                    )
    return {
        "valid": not errors,
        "dataset_status": "template_generated_unreviewed_pilot",
        "clusters_audited": len(pilot["clusters"]),
        "cases_audited": sum(
            len(cluster["cases"]) for cluster in pilot["clusters"]
        ),
        "method_first_prompts_audited": prompt_count,
        "privileged_or_label_leak_count": len(errors),
        "errors": errors,
        "model_invoked": False,
    }


def _find_keys(value: Any, forbidden: frozenset[str]) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in forbidden:
                found.add(key)
            found.update(_find_keys(child, forbidden))
    elif isinstance(value, list):
        for child in value:
            found.update(_find_keys(child, forbidden))
    return found


if __name__ == "__main__":
    main()
