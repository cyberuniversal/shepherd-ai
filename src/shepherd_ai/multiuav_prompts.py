"""Versioned, leak-resistant prompt contracts for MultiUAV methods."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

from shepherd_ai.multiuav_context import (
    AGENT_OBSERVATION_ENDPOINTS,
    validate_agent_visible_context,
)
from shepherd_ai.multiuav_grounding_validator import ENDPOINT_SPECS
from shepherd_ai.multiuav_methods import METHOD_SPECS


PROMPT_CONTRACT_VERSION = "multiuav_prompt_contract_v1"
_METHODS = {spec.method_id: spec for spec in METHOD_SPECS}

FINAL_OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "decision",
        "reason",
        "clarification_question",
        "api_plan",
    ],
    "properties": {
        "decision": {"enum": ["EXECUTE", "CLARIFY", "BLOCK"]},
        "reason": {"type": "string", "minLength": 1},
        "clarification_question": {
            "type": ["string", "null"],
        },
        "api_plan": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["endpoint", "parameters"],
                "properties": {
                    "endpoint": {"type": "string"},
                    "parameters": {"type": "object"},
                },
            },
        },
    },
}

EVIDENCE_LEDGER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "evidence",
        "missing_operator_facts",
        "conflicts",
        "provisional_decision",
        "reason",
    ],
    "properties": {
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["source_path", "claim"],
                "properties": {
                    "source_path": {"type": "string", "minLength": 1},
                    "claim": {"type": "string", "minLength": 1},
                },
            },
        },
        "missing_operator_facts": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        },
        "conflicts": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        },
        "provisional_decision": {
            "enum": ["EXECUTE", "CLARIFY", "BLOCK"],
        },
        "reason": {"type": "string", "minLength": 1},
    },
}


@dataclass(frozen=True)
class PromptMessage:
    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class PromptRequest:
    prompt_contract_version: str
    method_id: str
    call_index: int
    purpose: str
    messages: tuple[PromptMessage, ...]
    response_contract: Mapping[str, Any]
    context_sha256: str
    request_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_contract_version": self.prompt_contract_version,
            "method_id": self.method_id,
            "call_index": self.call_index,
            "purpose": self.purpose,
            "messages": [message.to_dict() for message in self.messages],
            "response_contract": dict(self.response_contract),
            "context_sha256": self.context_sha256,
            "request_sha256": self.request_sha256,
        }


def build_first_call_request(
    method_id: str,
    context: Mapping[str, Any],
) -> PromptRequest:
    """Build the first registered model call from AGENT-visible evidence."""

    spec = _method(method_id)
    validate_agent_visible_context(context)
    if method_id == "M3_stage_wise":
        common_payload = _common_payload(
            context,
            response_contract=EVIDENCE_LEDGER_SCHEMA,
        )
        messages = (
            PromptMessage(
                role="system",
                content=(
                    _common_system_text()
                    + "\nFirst create an evidence ledger. Do not create an API "
                    "plan in this call. Cite only source paths that exist in "
                    "AGENT_CONTEXT. List only operator-supplied facts that are "
                    "both required and unavailable through allowed observations."
                ),
            ),
            PromptMessage(
                role="user",
                content=_canonical_json(common_payload),
            ),
        )
        response_contract = EVIDENCE_LEDGER_SCHEMA
    else:
        common_payload = _common_payload(
            context,
            response_contract=FINAL_OUTPUT_SCHEMA,
        )
        messages = _planner_messages(common_payload)
        response_contract = FINAL_OUTPUT_SCHEMA
    return _request(
        method_id=method_id,
        call_index=0,
        purpose=spec.model_call_purposes[0],
        messages=messages,
        response_contract=response_contract,
        context=context,
    )


def build_second_call_request(
    method_id: str,
    context: Mapping[str, Any],
    *,
    first_raw_output: str,
    preplan_report: Mapping[str, Any] | None = None,
) -> PromptRequest:
    """Build the registered M3 or M4 second call."""

    spec = _method(method_id)
    validate_agent_visible_context(context)
    if spec.model_call_count != 2:
        raise ValueError(f"{method_id} does not have a second model call")
    if not isinstance(first_raw_output, str):
        raise TypeError("first_raw_output must be text")
    common_payload = _common_payload(
        context,
        response_contract=FINAL_OUTPUT_SCHEMA,
    )
    if method_id == "M3_stage_wise":
        if not isinstance(preplan_report, Mapping):
            raise ValueError("M3 second call requires a preplan report")
        task = {
            **common_payload,
            "FIRST_CALL_EVIDENCE_LEDGER_RAW": first_raw_output,
            "DETERMINISTIC_PREPLAN_REPORT": dict(preplan_report),
            "INSTRUCTION": (
                "Return the final strict decision and API plan. The second "
                "call is mandatory even when the final decision is CLARIFY "
                "or BLOCK. Do not silently repair or omit the preplan report."
            ),
        }
    elif method_id == "M4_post_plan_compute_matched":
        if preplan_report is not None:
            raise ValueError("M4 does not accept an M3 preplan report")
        task = {
            **common_payload,
            "FIRST_CALL_CANDIDATE_RAW": first_raw_output,
            "INSTRUCTION": (
                "Act as the learned post-plan validator. Return a complete "
                "final strict decision object. Preserve a valid candidate or "
                "replace it with a corrected EXECUTE, CLARIFY, or BLOCK "
                "object when visible evidence requires it."
            ),
        }
    else:
        raise ValueError(f"unsupported two-call method: {method_id}")
    messages = (
        PromptMessage(role="system", content=_common_system_text()),
        PromptMessage(role="user", content=_canonical_json(task)),
    )
    return _request(
        method_id=method_id,
        call_index=1,
        purpose=spec.model_call_purposes[1],
        messages=messages,
        response_contract=FINAL_OUTPUT_SCHEMA,
        context=context,
    )


def prompt_template_audit() -> dict[str, Any]:
    """Describe the frozen prompt invariants without embedding case data."""

    return {
        "prompt_contract_version": PROMPT_CONTRACT_VERSION,
        "methods": {
            spec.method_id: {
                "model_call_count": spec.model_call_count,
                "model_call_purposes": list(spec.model_call_purposes),
                "first_response_contract": (
                    "evidence_ledger"
                    if spec.method_id == "M3_stage_wise"
                    else "final_output"
                ),
                "second_response_contract": (
                    "final_output" if spec.model_call_count == 2 else None
                ),
            }
            for spec in METHOD_SPECS
        },
        "first_call_prompt_equivalence_group": [
            "M1_monolithic",
            "M2_post_plan_deterministic",
            "M4_post_plan_compute_matched",
        ],
        "visible_inputs": [
            "agent_context",
            "frozen_action_catalog",
            "allowed_observation_endpoints",
        ],
        "excluded_inputs": [
            "proposed_decision",
            "human_review_fields",
            "related_apis",
            "execution_check_apis",
            "official_reference_plan",
            "privileged_state",
        ],
    }


def _planner_messages(
    common_payload: Mapping[str, Any],
) -> tuple[PromptMessage, ...]:
    return (
        PromptMessage(role="system", content=_common_system_text()),
        PromptMessage(role="user", content=_canonical_json(common_payload)),
    )


def _common_system_text() -> str:
    return (
        "You are a high-level MultiUAV mission planner. Use only evidence in "
        "AGENT_CONTEXT, ACTION_CATALOG, and ALLOWED_OBSERVATIONS. Never invent "
        "UAV identifiers, endpoint names, coordinates, headings, distances, "
        "altitudes, messages, or unavailable facts. Return only one JSON "
        "object matching RESPONSE_CONTRACT. Do not emit Markdown or code."
    )


def _common_payload(
    context: Mapping[str, Any],
    *,
    response_contract: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "AGENT_CONTEXT": json.loads(_canonical_json(context)),
        "ACTION_CATALOG": {
            endpoint: {
                "required_parameters": sorted(spec.required),
                "optional_parameters": sorted(spec.optional),
            }
            for endpoint, spec in sorted(ENDPOINT_SPECS.items())
        },
        "ALLOWED_OBSERVATIONS": list(AGENT_OBSERVATION_ENDPOINTS),
        "RESPONSE_CONTRACT": response_contract,
    }


def _request(
    *,
    method_id: str,
    call_index: int,
    purpose: str,
    messages: tuple[PromptMessage, ...],
    response_contract: Mapping[str, Any],
    context: Mapping[str, Any],
) -> PromptRequest:
    request_payload = {
        "messages": [message.to_dict() for message in messages],
        "response_contract": response_contract,
    }
    return PromptRequest(
        prompt_contract_version=PROMPT_CONTRACT_VERSION,
        method_id=method_id,
        call_index=call_index,
        purpose=purpose,
        messages=messages,
        response_contract=response_contract,
        context_sha256=_sha256_json(context),
        request_sha256=_sha256_json(request_payload),
    )


def _method(method_id: str):
    try:
        return _METHODS[method_id]
    except KeyError as error:
        raise ValueError(f"unknown method id: {method_id}") from error


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
