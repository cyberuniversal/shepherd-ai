import json
import os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict

try:
    from backend.learned_parser import (
        ARTIFACT_SCHEMA,
        DEFAULT_ARTIFACT_PATH,
        BOUNDED_OUTPUT_FIELDS,
        StrictIntentAdapter,
        load_artifact,
    )
    from backend.parser_promotion import (
        DEFAULT_PROMOTION_REPORT_PATH,
        LEARNED_ARTIFACT_CANDIDATE,
        PROMOTION_SCHEMA,
    )
except ImportError:
    from learned_parser import (
        ARTIFACT_SCHEMA,
        DEFAULT_ARTIFACT_PATH,
        BOUNDED_OUTPUT_FIELDS,
        StrictIntentAdapter,
        load_artifact,
    )
    from parser_promotion import (
        DEFAULT_PROMOTION_REPORT_PATH,
        LEARNED_ARTIFACT_CANDIDATE,
        PROMOTION_SCHEMA,
    )


ENABLE_ENV = "SHEPHERD_ENABLE_LEARNED_PARSER"
RUNTIME_ENV = "SHEPHERD_PARSER_RUNTIME"
ARTIFACT_ENV = "SHEPHERD_LEARNED_PARSER_ARTIFACT"
PROMOTION_REPORT_ENV = "SHEPHERD_LEARNED_PARSER_PROMOTION_REPORT"
TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}
LEARNED_RUNTIME_VALUES = {"learned", "promoted_learned", "learned_parser"}


@dataclass
class PromotedParserStatus:
    enabled: bool
    ready: bool
    artifact_path: str
    promotion_report_path: str
    promoted: bool = False
    model_id: str | None = None
    artifact_digest: str | None = None
    parser: str | None = None
    error: str | None = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "ready": self.ready,
            "artifact_path": self.artifact_path,
            "promotion_report_path": self.promotion_report_path,
            "promoted": self.promoted,
            "model_id": self.model_id,
            "artifact_digest": self.artifact_digest,
            "parser": self.parser,
            "error": self.error,
        }


class PromotedLearnedParserRuntime:
    """Feature-flagged runtime loader for promotion-validated learned parser artifacts."""

    def __init__(self, env: Dict[str, str] | None = None):
        self.env = env or os.environ
        self.artifact_path = Path(self.env.get(ARTIFACT_ENV, str(DEFAULT_ARTIFACT_PATH)))
        self.promotion_report_path = Path(
            self.env.get(PROMOTION_REPORT_ENV, str(DEFAULT_PROMOTION_REPORT_PATH))
        )
        self.enabled = self._enabled_from_env()
        self.adapter: StrictIntentAdapter | None = None
        self._status = PromotedParserStatus(
            enabled=self.enabled,
            ready=False,
            artifact_path=str(self.artifact_path),
            promotion_report_path=str(self.promotion_report_path),
        )
        self.refresh()

    def _enabled_from_env(self) -> bool:
        if self.env.get(ENABLE_ENV, "").strip().lower() in TRUE_VALUES:
            return True
        return self.env.get(RUNTIME_ENV, "").strip().lower() in LEARNED_RUNTIME_VALUES

    def refresh(self) -> Dict[str, Any]:
        self.adapter = None
        self.enabled = self._enabled_from_env()
        self.artifact_path = Path(self.env.get(ARTIFACT_ENV, str(DEFAULT_ARTIFACT_PATH)))
        self.promotion_report_path = Path(
            self.env.get(PROMOTION_REPORT_ENV, str(DEFAULT_PROMOTION_REPORT_PATH))
        )
        self._status = PromotedParserStatus(
            enabled=self.enabled,
            ready=False,
            artifact_path=str(self.artifact_path),
            promotion_report_path=str(self.promotion_report_path),
        )
        if not self.enabled:
            return self.status()

        try:
            artifact = load_artifact(self.artifact_path)
            self._validate_artifact_contract(artifact)
            digest = self._validate_artifact_digest(artifact)
            promotion_report = self._load_promotion_report()
            self._validate_promotion_report(promotion_report, digest)
            self.adapter = StrictIntentAdapter(artifact)
            self._status = PromotedParserStatus(
                enabled=True,
                ready=True,
                artifact_path=str(self.artifact_path),
                promotion_report_path=str(self.promotion_report_path),
                promoted=True,
                model_id=artifact.get("model_id"),
                artifact_digest=digest,
                parser="learned_baseline",
            )
        except Exception as exc:
            self._status.error = str(exc)
        return self.status()

    def ready(self) -> bool:
        return self.enabled and self.adapter is not None and self._status.ready

    def status(self) -> Dict[str, Any]:
        return self._status.as_dict()

    def predict(self, command: str) -> Dict[str, Any]:
        if not self.ready() or self.adapter is None:
            raise RuntimeError(self._status.error or "Promoted learned parser is not ready")
        intent = self.adapter.predict(command)
        extras = sorted(set(intent) - BOUNDED_OUTPUT_FIELDS)
        if extras:
            raise ValueError(f"Learned parser produced unbounded fields: {extras}")
        return intent

    def _load_promotion_report(self) -> Dict[str, Any]:
        with self.promotion_report_path.open("r", encoding="utf-8") as handle:
            report = json.load(handle)
        if not isinstance(report, dict):
            raise ValueError("Promotion report must be a JSON object")
        return report

    def _validate_artifact_contract(self, artifact: Dict[str, Any]) -> None:
        if artifact.get("schema") != ARTIFACT_SCHEMA:
            raise ValueError(f"Unsupported learned parser artifact schema: {artifact.get('schema')}")
        contract = artifact.get("contract") or {}
        checks = {
            "bounded_intent_json_only": contract.get("output") == "bounded_intent_json_only",
            "dispatch_authority_false": contract.get("dispatch_authority") is False,
            "confirmation_required": contract.get("confirmation_required") is True,
            "deterministic_backend_required": contract.get("deterministic_backend_required") is True,
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise ValueError(f"Learned parser artifact contract failed: {', '.join(failed)}")
        artifact_fields = set(artifact.get("bounded_output_fields") or [])
        if artifact_fields and artifact_fields != BOUNDED_OUTPUT_FIELDS:
            raise ValueError("Learned parser artifact bounded output fields do not match runtime contract")

    def _validate_artifact_digest(self, artifact: Dict[str, Any]) -> str:
        expected = artifact.get("artifact_digest")
        if not expected:
            raise ValueError("Learned parser artifact is missing artifact_digest")
        clone = dict(artifact)
        clone.pop("artifact_digest", None)
        actual = sha256(
            json.dumps(clone, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if actual != expected:
            raise ValueError("Learned parser artifact digest mismatch")
        return expected

    def _validate_promotion_report(self, report: Dict[str, Any], artifact_digest: str) -> None:
        if report.get("schema") != PROMOTION_SCHEMA:
            raise ValueError(f"Unsupported parser promotion schema: {report.get('schema')}")
        if report.get("candidate_type") != LEARNED_ARTIFACT_CANDIDATE:
            raise ValueError("Promotion report candidate is not a learned parser artifact")
        if report.get("promoted") is not True:
            raise ValueError("Learned parser promotion report is not promoted")
        if report.get("artifact_digest") != artifact_digest:
            raise ValueError("Promotion report digest does not match learned parser artifact")
        candidate_path = report.get("candidate_path")
        if candidate_path and not self._same_path(candidate_path, self.artifact_path):
            raise ValueError("Promotion report candidate_path does not match learned parser artifact")
        contract_checks = report.get("contract_checks") or {}
        if contract_checks.get("passed") is not True:
            raise ValueError("Promotion report contract checks did not pass")

    def _same_path(self, left: str | Path, right: str | Path) -> bool:
        try:
            return Path(left).resolve() == Path(right).resolve()
        except OSError:
            return str(Path(left)) == str(Path(right))
