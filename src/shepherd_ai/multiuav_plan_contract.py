"""Strict model-output contract for the MultiUAV comparison methods."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping


DECISIONS = frozenset({"EXECUTE", "CLARIFY", "BLOCK"})
OUTPUT_FIELDS = frozenset(
    {"decision", "reason", "clarification_question", "api_plan"}
)
API_CALL_FIELDS = frozenset({"endpoint", "parameters"})


@dataclass(frozen=True)
class ApiCall:
    endpoint: str
    parameters: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "parameters": self.parameters,
        }


@dataclass(frozen=True)
class StrictModelOutput:
    decision: str
    reason: str
    clarification_question: str | None
    api_plan: tuple[ApiCall, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "clarification_question": self.clarification_question,
            "api_plan": [call.to_dict() for call in self.api_plan],
        }


@dataclass(frozen=True)
class ModelOutputParse:
    parse_status: str
    raw_output: str
    parsed: StrictModelOutput | None = None
    error_code: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "parse_status": self.parse_status,
            "raw_output": self.raw_output,
            "parsed": self.parsed.to_dict() if self.parsed else None,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


class ContractError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def parse_strict_model_output(raw_output: str) -> ModelOutputParse:
    """Parse one strict JSON object and preserve every failure as PARSE_ERROR."""

    if not isinstance(raw_output, str):
        raise TypeError("raw_output must be text")
    try:
        payload = json.loads(
            raw_output,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_number,
        )
        parsed = _validate_payload(payload)
    except json.JSONDecodeError as error:
        return _parse_error(
            raw_output,
            "invalid_json",
            f"{error.msg} at line {error.lineno} column {error.colno}",
        )
    except ContractError as error:
        return _parse_error(raw_output, error.code, str(error))
    return ModelOutputParse(
        parse_status="PARSED",
        raw_output=raw_output,
        parsed=parsed,
    )


def _validate_payload(payload: Any) -> StrictModelOutput:
    if not isinstance(payload, Mapping):
        raise ContractError("root_not_object", "output root must be an object")
    if set(payload) != OUTPUT_FIELDS:
        raise ContractError(
            "output_schema_mismatch",
            f"output fields must be exactly {sorted(OUTPUT_FIELDS)}",
        )
    decision = payload["decision"]
    if not isinstance(decision, str) or decision not in DECISIONS:
        raise ContractError(
            "invalid_decision",
            "decision must be exactly EXECUTE, CLARIFY, or BLOCK",
        )
    reason = _nonempty_text(payload["reason"], "reason")
    question = payload["clarification_question"]
    plan = payload["api_plan"]
    if not isinstance(plan, list):
        raise ContractError("api_plan_not_array", "api_plan must be an array")

    if decision == "EXECUTE":
        if question is not None:
            raise ContractError(
                "execute_has_question",
                "EXECUTE requires clarification_question=null",
            )
        if not plan:
            raise ContractError(
                "empty_execute_plan",
                "EXECUTE requires a non-empty api_plan",
            )
    elif decision == "CLARIFY":
        question = _nonempty_text(question, "clarification_question")
        if plan:
            raise ContractError(
                "clarify_has_plan",
                "CLARIFY requires an empty api_plan",
            )
    else:
        if question is not None:
            raise ContractError(
                "block_has_question",
                "BLOCK requires clarification_question=null",
            )
        if plan:
            raise ContractError(
                "block_has_plan",
                "BLOCK requires an empty api_plan",
            )

    api_calls = tuple(
        _validate_api_call(call, index=index)
        for index, call in enumerate(plan)
    )
    return StrictModelOutput(
        decision=decision,
        reason=reason,
        clarification_question=question,
        api_plan=api_calls,
    )


def _validate_api_call(value: Any, *, index: int) -> ApiCall:
    if not isinstance(value, Mapping):
        raise ContractError(
            "api_call_not_object",
            f"api_plan[{index}] must be an object",
        )
    if set(value) != API_CALL_FIELDS:
        raise ContractError(
            "api_call_schema_mismatch",
            f"api_plan[{index}] fields must be exactly {sorted(API_CALL_FIELDS)}",
        )
    endpoint = _nonempty_text(value["endpoint"], f"api_plan[{index}].endpoint")
    has_whitespace = any(character.isspace() for character in endpoint)
    if not endpoint.startswith("/") or has_whitespace:
        raise ContractError(
            "invalid_endpoint",
            f"api_plan[{index}].endpoint must be an absolute API path",
        )
    parameters = value["parameters"]
    if not isinstance(parameters, dict):
        raise ContractError(
            "parameters_not_object",
            f"api_plan[{index}].parameters must be an object",
        )
    _reject_empty_parameter_values(parameters, path=f"api_plan[{index}].parameters")
    return ApiCall(endpoint=endpoint, parameters=dict(parameters))


def _reject_empty_parameter_values(value: Any, *, path: str) -> None:
    if value is None:
        raise ContractError("empty_parameter_value", f"{path} cannot be null")
    if isinstance(value, str) and not value.strip():
        raise ContractError("empty_parameter_value", f"{path} cannot be blank")
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str) or not key.strip():
                raise ContractError(
                    "empty_parameter_name",
                    f"{path} contains an empty parameter name",
                )
            _reject_empty_parameter_values(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        if not value:
            raise ContractError(
                "empty_parameter_value",
                f"{path} cannot contain an empty array value",
            )
        for index, child in enumerate(value):
            _reject_empty_parameter_values(child, path=f"{path}[{index}]")


def _nonempty_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(
            "empty_required_text",
            f"{field} must be non-empty text",
        )
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("duplicate_json_key", f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_number(value: str) -> None:
    raise ContractError("nonfinite_number", f"non-finite JSON number: {value}")


def _parse_error(raw_output: str, code: str, message: str) -> ModelOutputParse:
    return ModelOutputParse(
        parse_status="PARSE_ERROR",
        raw_output=raw_output,
        error_code=code,
        error_message=message,
    )
