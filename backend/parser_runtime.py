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
        TRANSFORMER_MODEL_CANDIDATE,
    )
    from backend.transformer_parser import (
        DEFAULT_TRANSFORMER_MODEL_DIR,
        TRANSFORMER_MODEL_CONTRACT_SCHEMA,
        TransformerIntentAdapter,
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
        TRANSFORMER_MODEL_CANDIDATE,
    )
    from transformer_parser import (
        DEFAULT_TRANSFORMER_MODEL_DIR,
        TRANSFORMER_MODEL_CONTRACT_SCHEMA,
        TransformerIntentAdapter,
    )


ENABLE_ENV = "SHEPHERD_ENABLE_LEARNED_PARSER"
RUNTIME_ENV = "SHEPHERD_PARSER_RUNTIME"
SHADOW_ENV = "SHEPHERD_SHADOW_LEARNED_PARSER"
ARTIFACT_ENV = "SHEPHERD_LEARNED_PARSER_ARTIFACT"
MODEL_DIR_ENV = "SHEPHERD_LEARNED_PARSER_MODEL_DIR"
PROMOTION_REPORT_ENV = "SHEPHERD_LEARNED_PARSER_PROMOTION_REPORT"
TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}
LEARNED_RUNTIME_VALUES = {"learned", "promoted_learned", "learned_parser"}


@dataclass
class PromotedParserStatus:
    enabled: bool
    shadow_enabled: bool
    ready: bool
    artifact_path: str
    promotion_report_path: str
    candidate_type: str | None = None
    candidate_path: str | None = None
    promoted: bool = False
    model_id: str | None = None
    artifact_digest: str | None = None
    parser: str | None = None
    error: str | None = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "active": self.enabled,
            "shadow_enabled": self.shadow_enabled,
            "ready": self.ready,
            "artifact_path": self.artifact_path,
            "promotion_report_path": self.promotion_report_path,
            "candidate_type": self.candidate_type,
            "candidate_path": self.candidate_path or self.artifact_path,
            "promoted": self.promoted,
            "model_id": self.model_id,
            "artifact_digest": self.artifact_digest,
            "parser": self.parser,
            "error": self.error,
        }


class PromotedLearnedParserRuntime:
    """Feature-flagged runtime loader for promotion-validated parser candidates."""

    def __init__(
        self,
        env: Dict[str, str] | None = None,
        *,
        learned_adapter_cls=StrictIntentAdapter,
        transformer_adapter_cls=TransformerIntentAdapter,
    ):
        self.env = env or os.environ
        self.learned_adapter_cls = learned_adapter_cls
        self.transformer_adapter_cls = transformer_adapter_cls
        self.artifact_path = Path(self.env.get(ARTIFACT_ENV, str(DEFAULT_ARTIFACT_PATH)))
        self.model_dir = Path(self.env.get(MODEL_DIR_ENV, str(DEFAULT_TRANSFORMER_MODEL_DIR)))
        self.promotion_report_path = Path(
            self.env.get(PROMOTION_REPORT_ENV, str(DEFAULT_PROMOTION_REPORT_PATH))
        )
        self.enabled = self._enabled_from_env()
        self.adapter = None
        self._status = PromotedParserStatus(
            enabled=self.enabled,
            shadow_enabled=self._shadow_enabled_from_env(),
            ready=False,
            artifact_path=str(self.artifact_path),
            promotion_report_path=str(self.promotion_report_path),
        )
        self.refresh()

    def _enabled_from_env(self) -> bool:
        if self.env.get(ENABLE_ENV, "").strip().lower() in TRUE_VALUES:
            return True
        return self.env.get(RUNTIME_ENV, "").strip().lower() in LEARNED_RUNTIME_VALUES

    def _shadow_enabled_from_env(self) -> bool:
        return self.env.get(SHADOW_ENV, "").strip().lower() in TRUE_VALUES

    def refresh(self) -> Dict[str, Any]:
        self.adapter = None
        self.enabled = self._enabled_from_env()
        shadow_enabled = self._shadow_enabled_from_env()
        self.artifact_path = Path(self.env.get(ARTIFACT_ENV, str(DEFAULT_ARTIFACT_PATH)))
        self.model_dir = Path(self.env.get(MODEL_DIR_ENV, str(DEFAULT_TRANSFORMER_MODEL_DIR)))
        self.promotion_report_path = Path(
            self.env.get(PROMOTION_REPORT_ENV, str(DEFAULT_PROMOTION_REPORT_PATH))
        )
        self._status = PromotedParserStatus(
            enabled=self.enabled,
            shadow_enabled=shadow_enabled,
            ready=False,
            artifact_path=str(self.artifact_path),
            promotion_report_path=str(self.promotion_report_path),
        )
        if not self.enabled and not shadow_enabled:
            return self.status()

        try:
            promotion_report = self._load_promotion_report()
            candidate_type = promotion_report.get("candidate_type")
            if candidate_type == TRANSFORMER_MODEL_CANDIDATE:
                self._load_transformer_runtime(promotion_report, shadow_enabled=shadow_enabled)
                return self.status()
            self._load_learned_artifact_runtime(promotion_report, shadow_enabled=shadow_enabled)
        except Exception as exc:
            self._status.error = str(exc)
        return self.status()

    def _load_learned_artifact_runtime(self, promotion_report: Dict[str, Any], *, shadow_enabled: bool) -> None:
        artifact = load_artifact(self.artifact_path)
        self._validate_artifact_contract(artifact)
        digest = self._validate_artifact_digest(artifact)
        self._validate_promotion_report(
            promotion_report,
            digest,
            candidate_type=LEARNED_ARTIFACT_CANDIDATE,
            candidate_path=self.artifact_path,
        )
        self.adapter = self.learned_adapter_cls(artifact)
        self._status = PromotedParserStatus(
            enabled=self.enabled,
            shadow_enabled=shadow_enabled,
            ready=True,
            artifact_path=str(self.artifact_path),
            promotion_report_path=str(self.promotion_report_path),
            candidate_type=LEARNED_ARTIFACT_CANDIDATE,
            candidate_path=str(self.artifact_path),
            promoted=True,
            model_id=artifact.get("model_id"),
            artifact_digest=digest,
            parser="learned_baseline",
        )

    def _load_transformer_runtime(self, promotion_report: Dict[str, Any], *, shadow_enabled: bool) -> None:
        model_dir = self._model_dir_from_report(promotion_report)
        contract = self._load_transformer_contract(model_dir)
        digest = self._validate_transformer_contract(contract)
        self._validate_promotion_report(
            promotion_report,
            digest,
            candidate_type=TRANSFORMER_MODEL_CANDIDATE,
            candidate_path=model_dir,
        )
        self.adapter = self.transformer_adapter_cls(model_dir)
        self._status = PromotedParserStatus(
            enabled=self.enabled,
            shadow_enabled=shadow_enabled,
            ready=True,
            artifact_path=str(model_dir),
            promotion_report_path=str(self.promotion_report_path),
            candidate_type=TRANSFORMER_MODEL_CANDIDATE,
            candidate_path=str(model_dir),
            promoted=True,
            model_id=contract.get("model_id"),
            artifact_digest=digest,
            parser="transformer_seq2seq",
        )

    def ready(self) -> bool:
        return self.enabled and self.adapter is not None and self._status.ready

    def shadow_ready(self) -> bool:
        return self._status.shadow_enabled and self.adapter is not None and self._status.ready

    def status(self) -> Dict[str, Any]:
        return self._status.as_dict()

    def predict(self, command: str) -> Dict[str, Any]:
        if not self.ready() or self.adapter is None:
            raise RuntimeError(self._status.error or "Promoted learned parser is not ready")
        return self._predict_with_adapter(command)

    def predict_shadow(self, command: str) -> Dict[str, Any]:
        if not self.shadow_ready() or self.adapter is None:
            raise RuntimeError(self._status.error or "Promoted learned parser shadow mode is not ready")
        return self._predict_with_adapter(command)

    def _predict_with_adapter(self, command: str) -> Dict[str, Any]:
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

    def _model_dir_from_report(self, report: Dict[str, Any]) -> Path:
        configured = self.env.get(MODEL_DIR_ENV)
        if configured:
            return Path(configured)
        if report.get("candidate_path"):
            return Path(report["candidate_path"])
        legacy_path = self.env.get(ARTIFACT_ENV)
        if legacy_path:
            return Path(legacy_path)
        return DEFAULT_TRANSFORMER_MODEL_DIR

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
        if artifact_fields and not artifact_fields.issubset(BOUNDED_OUTPUT_FIELDS):
            raise ValueError("Learned parser artifact bounded output fields are outside runtime contract")

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

    def _load_transformer_contract(self, model_dir: Path) -> Dict[str, Any]:
        contract_path = model_dir / "shepherd_model_contract.json"
        with contract_path.open("r", encoding="utf-8") as handle:
            contract = json.load(handle)
        if not isinstance(contract, dict):
            raise ValueError("Transformer parser contract must be a JSON object")
        return contract

    def _validate_transformer_contract(self, contract: Dict[str, Any]) -> str:
        if contract.get("schema") != TRANSFORMER_MODEL_CONTRACT_SCHEMA:
            raise ValueError(f"Unsupported transformer parser contract schema: {contract.get('schema')}")
        runtime_contract = contract.get("contract") or {}
        checks = {
            "bounded_intent_json_only": runtime_contract.get("output") == "bounded_intent_json_only",
            "dispatch_authority_false": runtime_contract.get("dispatch_authority") is False,
            "confirmation_required": runtime_contract.get("confirmation_required") is True,
            "deterministic_backend_required": runtime_contract.get("deterministic_backend_required") is True,
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise ValueError(f"Transformer parser contract failed: {', '.join(failed)}")
        artifact_fields = set(contract.get("bounded_output_fields") or [])
        if artifact_fields and not artifact_fields.issubset(BOUNDED_OUTPUT_FIELDS):
            raise ValueError("Transformer parser bounded output fields are outside runtime contract")
        expected = contract.get("model_digest")
        if not expected:
            raise ValueError("Transformer parser contract is missing model_digest")
        clone = dict(contract)
        clone.pop("model_digest", None)
        actual = sha256(
            json.dumps(clone, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if actual != expected:
            raise ValueError("Transformer parser contract digest mismatch")
        return expected

    def _validate_promotion_report(
        self,
        report: Dict[str, Any],
        artifact_digest: str,
        *,
        candidate_type: str,
        candidate_path: str | Path,
    ) -> None:
        if report.get("schema") != PROMOTION_SCHEMA:
            raise ValueError(f"Unsupported parser promotion schema: {report.get('schema')}")
        if report.get("candidate_type") != candidate_type:
            raise ValueError(f"Promotion report candidate is not {candidate_type}")
        if report.get("promoted") is not True:
            raise ValueError("Parser promotion report is not promoted")
        if report.get("artifact_digest") != artifact_digest:
            raise ValueError("Promotion report digest does not match parser candidate")
        report_candidate_path = report.get("candidate_path")
        if report_candidate_path and not self._same_path(report_candidate_path, candidate_path):
            raise ValueError("Promotion report candidate_path does not match parser candidate")
        contract_checks = report.get("contract_checks") or {}
        if contract_checks.get("passed") is not True:
            raise ValueError("Promotion report contract checks did not pass")

    def _same_path(self, left: str | Path, right: str | Path) -> bool:
        try:
            return Path(left).resolve() == Path(right).resolve()
        except OSError:
            return str(Path(left)) == str(Path(right))
