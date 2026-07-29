"""Frozen method definitions and model-call budgets for the MultiUAV study."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MethodSpec:
    method_id: str
    model_call_count: int
    model_call_purposes: tuple[str, ...]
    deterministic_preplan_gate: bool
    deterministic_postplan_gate: bool
    learned_postplan_validator: bool

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["model_call_purposes"] = list(self.model_call_purposes)
        return payload


METHOD_SPECS = (
    MethodSpec(
        method_id="M1_monolithic",
        model_call_count=1,
        model_call_purposes=("decision_and_api_plan",),
        deterministic_preplan_gate=False,
        deterministic_postplan_gate=False,
        learned_postplan_validator=False,
    ),
    MethodSpec(
        method_id="M2_post_plan_deterministic",
        model_call_count=1,
        model_call_purposes=("decision_and_api_plan",),
        deterministic_preplan_gate=False,
        deterministic_postplan_gate=True,
        learned_postplan_validator=False,
    ),
    MethodSpec(
        method_id="M3_stage_wise",
        model_call_count=2,
        model_call_purposes=(
            "evidence_ledger_and_provisional_decision",
            "api_plan_or_nonexecute_decision_finalization",
        ),
        deterministic_preplan_gate=True,
        deterministic_postplan_gate=True,
        learned_postplan_validator=False,
    ),
    MethodSpec(
        method_id="M4_post_plan_compute_matched",
        model_call_count=2,
        model_call_purposes=(
            "decision_and_api_plan",
            "learned_postplan_validation",
        ),
        deterministic_preplan_gate=False,
        deterministic_postplan_gate=True,
        learned_postplan_validator=True,
    ),
)


def validate_method_specs(
    specs: tuple[MethodSpec, ...] = METHOD_SPECS,
) -> dict[str, object]:
    """Reject method drift that would invalidate the registered comparison."""

    by_id = {spec.method_id: spec for spec in specs}
    expected_ids = {
        "M1_monolithic",
        "M2_post_plan_deterministic",
        "M3_stage_wise",
        "M4_post_plan_compute_matched",
    }
    if set(by_id) != expected_ids or len(specs) != len(expected_ids):
        raise ValueError("method registry must contain M1 through M4 exactly once")
    for spec in specs:
        if spec.model_call_count != len(spec.model_call_purposes):
            raise ValueError(f"{spec.method_id}: call count and purposes differ")
    if by_id["M1_monolithic"].model_call_count != 1:
        raise ValueError("M1 must use one model call")
    if by_id["M2_post_plan_deterministic"].model_call_count != 1:
        raise ValueError("M2 must use one model call")
    if by_id["M3_stage_wise"].model_call_count != 2:
        raise ValueError("M3 must use two model calls")
    if by_id["M4_post_plan_compute_matched"].model_call_count != 2:
        raise ValueError("M4 must use two model calls")
    if (
        by_id["M3_stage_wise"].model_call_count
        != by_id["M4_post_plan_compute_matched"].model_call_count
    ):
        raise ValueError("M3 and M4 must be exactly model-call matched")
    return {
        "valid": True,
        "method_count": len(specs),
        "call_counts": {
            method_id: by_id[method_id].model_call_count
            for method_id in sorted(by_id)
        },
        "matching_scope": (
            "model_call_count_only_tokens_latency_memory_and_energy_measured"
        ),
    }
