"""Immutable model-revision registry for the MultiUAV study."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Callable, Mapping
from urllib.parse import quote


HF_MODEL_API_ROOT = "https://huggingface.co/api/models"
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class ModelRevision:
    model_id: str
    revision: str
    role: str

    @property
    def revision_api_url(self) -> str:
        model_path = "/".join(
            quote(part, safe="") for part in self.model_id.split("/")
        )
        return f"{HF_MODEL_API_ROOT}/{model_path}/revision/{self.revision}"

    def to_dict(self) -> dict[str, str]:
        return {
            **asdict(self),
            "revision_api_url": self.revision_api_url,
        }


REGISTERED_MODEL_REVISIONS = (
    ModelRevision(
        model_id="Qwen/Qwen2.5-3B-Instruct",
        revision="aa8e72537993ba99e69dfaafa59ed015b17504d1",
        role="primary_scale",
    ),
    ModelRevision(
        model_id="Qwen/Qwen2.5-7B-Instruct",
        revision="a09a35458c702b33eeacc393d103063234e8bc28",
        role="confirmation_scale",
    ),
)


def validate_model_revisions(
    revisions: tuple[ModelRevision, ...] = REGISTERED_MODEL_REVISIONS,
) -> dict[str, Any]:
    """Validate immutable syntax and uniqueness without network access."""

    errors: list[str] = []
    model_ids = [item.model_id for item in revisions]
    roles = [item.role for item in revisions]
    if len(revisions) != 2:
        errors.append("exactly two model revisions are required")
    if len(set(model_ids)) != len(model_ids):
        errors.append("model ids must be unique")
    if len(set(roles)) != len(roles):
        errors.append("model roles must be unique")
    for item in revisions:
        if not item.model_id.startswith("Qwen/Qwen2.5-"):
            errors.append(f"unexpected model family: {item.model_id}")
        if _COMMIT_PATTERN.fullmatch(item.revision) is None:
            errors.append(
                f"revision must be a lowercase 40-character commit: {item.model_id}"
            )
        if not item.role:
            errors.append(f"model role is empty: {item.model_id}")
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "valid": True,
        "model_count": len(revisions),
        "model_ids": model_ids,
        "roles": roles,
        "all_revisions_immutable": True,
    }


def build_model_revision_audit(
    *,
    fetch_json: Callable[[str], Mapping[str, Any]] | None,
    resolved_at_utc: str,
) -> dict[str, Any]:
    """Build a revision audit, optionally verifying pinned endpoints remotely."""

    local_validation = validate_model_revisions()
    remote_records: list[dict[str, Any]] = []
    errors: list[str] = []
    for item in REGISTERED_MODEL_REVISIONS:
        record = {
            **item.to_dict(),
            "remote_verified": False,
            "reported_model_id": None,
            "reported_revision": None,
            "last_modified": None,
            "reported_license": None,
            "reported_license_name": None,
            "reported_license_link": None,
        }
        if fetch_json is not None:
            try:
                payload = fetch_json(item.revision_api_url)
            except Exception as error:  # network errors must remain audit data
                errors.append(
                    f"remote verification failed for {item.model_id}: "
                    f"{type(error).__name__}: {error}"
                )
            else:
                record["reported_model_id"] = payload.get("id")
                record["reported_revision"] = payload.get("sha")
                record["last_modified"] = payload.get("lastModified")
                card_data = payload.get("cardData")
                if isinstance(card_data, Mapping):
                    record["reported_license"] = card_data.get("license")
                    record["reported_license_name"] = card_data.get(
                        "license_name"
                    )
                    record["reported_license_link"] = card_data.get(
                        "license_link"
                    )
                record["remote_verified"] = (
                    payload.get("id") == item.model_id
                    and payload.get("sha") == item.revision
                )
                if not record["remote_verified"]:
                    errors.append(
                        f"remote revision mismatch for {item.model_id}"
                    )
        remote_records.append(record)

    remote_performed = fetch_json is not None
    return {
        "schema_version": 1,
        "valid": not errors and (
            not remote_performed
            or all(record["remote_verified"] for record in remote_records)
        ),
        "resolved_at_utc": resolved_at_utc,
        "local_validation": local_validation,
        "remote_verification_performed": remote_performed,
        "models": remote_records,
        "errors": errors,
        "weights_downloaded": False,
        "model_invoked": False,
        "claim_status": (
            "immutable_model_metadata_verified_no_weights_or_inference"
            if remote_performed and not errors
            else "immutable_model_registry_validated_offline_only"
        ),
    }
