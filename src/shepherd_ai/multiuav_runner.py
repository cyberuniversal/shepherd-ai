"""Provider-independent M1-M4 runner with exact model-call accounting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from shepherd_ai.multiuav_context import validate_agent_visible_context
from shepherd_ai.multiuav_grounding_validator import validate_grounded_plan
from shepherd_ai.multiuav_ledger_contract import (
    parse_evidence_ledger,
    validate_evidence_ledger,
)
from shepherd_ai.multiuav_methods import METHOD_SPECS
from shepherd_ai.multiuav_plan_contract import parse_strict_model_output
from shepherd_ai.multiuav_prompts import (
    PromptRequest,
    build_first_call_request,
    build_second_call_request,
)


_METHODS = {spec.method_id: spec for spec in METHOD_SPECS}
RUNNABLE_CASE_STATUSES = frozenset(
    {"approved_evaluation_case", "synthetic_unit_fixture"}
)


@dataclass(frozen=True)
class GenerationResult:
    raw_output: str
    generation_status: str = "GENERATED"
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: float | None = None
    metadata: Mapping[str, Any] | None = None
    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_output": self.raw_output,
            "generation_status": self.generation_status,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "latency_ms": self.latency_ms,
            "metadata": dict(self.metadata or {}),
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


class ModelBackend(Protocol):
    def generate(self, request: PromptRequest) -> GenerationResult:
        """Return one raw model generation for the supplied request."""


@dataclass(frozen=True)
class ModelCallRecord:
    request: PromptRequest
    generation: GenerationResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "generation": self.generation.to_dict(),
        }


@dataclass(frozen=True)
class MethodCaseResult:
    case_id: str
    case_status: str
    method_id: str
    expected_model_call_count: int
    actual_model_call_count: int
    calls: tuple[ModelCallRecord, ...]
    intermediate_ledger: Mapping[str, Any] | None
    preplan_report: Mapping[str, Any] | None
    final_parse: Mapping[str, Any]
    deterministic_postplan_report: Mapping[str, Any] | None
    resource_measurement: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "case_status": self.case_status,
            "method_id": self.method_id,
            "expected_model_call_count": self.expected_model_call_count,
            "actual_model_call_count": self.actual_model_call_count,
            "calls": [call.to_dict() for call in self.calls],
            "intermediate_ledger": (
                dict(self.intermediate_ledger)
                if self.intermediate_ledger is not None
                else None
            ),
            "preplan_report": (
                dict(self.preplan_report)
                if self.preplan_report is not None
                else None
            ),
            "final_parse": dict(self.final_parse),
            "deterministic_postplan_report": (
                dict(self.deterministic_postplan_report)
                if self.deterministic_postplan_report is not None
                else None
            ),
            "resource_measurement": (
                dict(self.resource_measurement)
                if self.resource_measurement is not None
                else None
            ),
        }


def run_method_case(
    *,
    case_id: str,
    case_status: str,
    method_id: str,
    context: Mapping[str, Any],
    backend: ModelBackend,
) -> MethodCaseResult:
    """Run one approved or synthetic fixture case under one frozen method."""

    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("case_id must be non-empty text")
    if case_status not in RUNNABLE_CASE_STATUSES:
        raise ValueError(
            "case_status is not approved for model execution: "
            f"{case_status!r}"
        )
    try:
        spec = _METHODS[method_id]
    except KeyError as error:
        raise ValueError(f"unknown method id: {method_id}") from error
    validate_agent_visible_context(context)

    calls: list[ModelCallRecord] = []
    first_request = build_first_call_request(method_id, context)
    first_generation = _generate(backend, first_request)
    calls.append(ModelCallRecord(first_request, first_generation))

    intermediate: Mapping[str, Any] | None = None
    preplan: Mapping[str, Any] | None = None
    final_generation = first_generation
    if method_id == "M3_stage_wise":
        ledger_parse = parse_evidence_ledger(first_generation.raw_output)
        preplan_result = validate_evidence_ledger(ledger_parse, context)
        intermediate = ledger_parse.to_dict()
        preplan = preplan_result.to_dict()
        second_request = build_second_call_request(
            method_id,
            context,
            first_raw_output=first_generation.raw_output,
            preplan_report=preplan,
        )
        final_generation = _generate(backend, second_request)
        calls.append(ModelCallRecord(second_request, final_generation))
    elif method_id == "M4_post_plan_compute_matched":
        second_request = build_second_call_request(
            method_id,
            context,
            first_raw_output=first_generation.raw_output,
        )
        final_generation = _generate(backend, second_request)
        calls.append(ModelCallRecord(second_request, final_generation))

    if len(calls) != spec.model_call_count:
        raise RuntimeError(
            f"{method_id}: expected {spec.model_call_count} calls, "
            f"recorded {len(calls)}"
        )
    final_parse = parse_strict_model_output(final_generation.raw_output)
    postplan: Mapping[str, Any] | None = None
    if spec.deterministic_postplan_gate and final_parse.parsed is not None:
        postplan = validate_grounded_plan(
            final_parse.parsed,
            context,
        ).to_dict()
    return MethodCaseResult(
        case_id=case_id.strip(),
        case_status=case_status,
        method_id=method_id,
        expected_model_call_count=spec.model_call_count,
        actual_model_call_count=len(calls),
        calls=tuple(calls),
        intermediate_ledger=intermediate,
        preplan_report=preplan,
        final_parse=final_parse.to_dict(),
        deterministic_postplan_report=postplan,
    )


def _generate(
    backend: ModelBackend,
    request: PromptRequest,
) -> GenerationResult:
    try:
        result = backend.generate(request)
    except Exception as error:
        return GenerationResult(
            raw_output="",
            generation_status="BACKEND_ERROR",
            metadata={"backend_type": type(backend).__name__},
            error_type=type(error).__name__,
            error_message=str(error),
        )
    if not isinstance(result, GenerationResult):
        return GenerationResult(
            raw_output="",
            generation_status="BACKEND_PROTOCOL_ERROR",
            metadata={"backend_type": type(backend).__name__},
            error_type="TypeError",
            error_message="backend.generate must return GenerationResult",
        )
    if not isinstance(result.raw_output, str):
        return GenerationResult(
            raw_output="",
            generation_status="BACKEND_PROTOCOL_ERROR",
            metadata={"backend_type": type(backend).__name__},
            error_type="TypeError",
            error_message="generation raw_output must be text",
        )
    return result
