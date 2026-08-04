"""Config-bound JSONL persistence and compact ZIP checkpoints."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable, Mapping
import zipfile

from shepherd_ai.multiuav_methods import METHOD_SPECS
from shepherd_ai.multiuav_model_revisions import REGISTERED_MODEL_REVISIONS
from shepherd_ai.multiuav_prompts import PROMPT_CONTRACT_VERSION
from shepherd_ai.multiuav_runner import MethodCaseResult


CHECKPOINT_SCHEMA_VERSION = 3
_METHOD_IDS = frozenset(spec.method_id for spec in METHOD_SPECS)
_MODEL_REVISIONS = {
    item.model_id: item.revision for item in REGISTERED_MODEL_REVISIONS
}
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class RunConfig:
    run_id: str
    study_id: str
    run_kind: str
    model_id: str
    model_revision: str
    methods: tuple[str, ...]
    dataset_sha256: str
    prompt_contract_version: str
    decoding: Mapping[str, Any]
    code_commit: str
    resource_repetition: int | None = None
    hardware_protocol_sha256: str | None = None
    resource_condition_order: int | None = None
    resource_schedule_sha256: str | None = None

    def validate(self) -> None:
        if not self.run_id.strip() or not self.study_id.strip():
            raise ValueError("run_id and study_id must be non-empty")
        if self.run_kind not in {"accuracy", "resource", "synthetic_smoke"}:
            raise ValueError("unsupported run_kind")
        if _MODEL_REVISIONS.get(self.model_id) != self.model_revision:
            raise ValueError("model id/revision is absent from the frozen registry")
        if not self.methods or len(set(self.methods)) != len(self.methods):
            raise ValueError("methods must be non-empty and unique")
        if not set(self.methods) <= _METHOD_IDS:
            raise ValueError("run config contains an unknown method")
        if _SHA256_PATTERN.fullmatch(self.dataset_sha256) is None:
            raise ValueError("dataset_sha256 must be lowercase SHA-256")
        if self.prompt_contract_version != PROMPT_CONTRACT_VERSION:
            raise ValueError("prompt contract version differs from the frozen version")
        if self.decoding.get("do_sample") is not False:
            raise ValueError("deterministic decoding requires do_sample=false")
        if self.decoding.get("num_beams") != 1:
            raise ValueError("deterministic decoding requires num_beams=1")
        max_tokens = self.decoding.get("max_new_tokens")
        if (
            not isinstance(max_tokens, int)
            or isinstance(max_tokens, bool)
            or max_tokens <= 0
        ):
            raise ValueError("max_new_tokens must be a positive integer")
        if _COMMIT_PATTERN.fullmatch(self.code_commit) is None:
            raise ValueError("code_commit must be a lowercase 40-character commit")
        if self.run_kind == "resource":
            if self.resource_repetition not in {1, 2, 3}:
                raise ValueError("resource runs require repetition 1, 2, or 3")
            if (
                self.hardware_protocol_sha256 is None
                or _SHA256_PATTERN.fullmatch(self.hardware_protocol_sha256) is None
            ):
                raise ValueError("resource runs require hardware protocol SHA-256")
            if (
                not isinstance(self.resource_condition_order, int)
                or isinstance(self.resource_condition_order, bool)
                or self.resource_condition_order < 1
            ):
                raise ValueError("resource runs require a positive condition order")
            if (
                self.resource_schedule_sha256 is None
                or _SHA256_PATTERN.fullmatch(self.resource_schedule_sha256) is None
            ):
                raise ValueError("resource runs require resource schedule SHA-256")
        elif (
            self.resource_repetition is not None
            or self.hardware_protocol_sha256 is not None
            or self.resource_condition_order is not None
            or self.resource_schedule_sha256 is not None
        ):
            raise ValueError("resource metadata is only valid for resource runs")

    @property
    def config_hash(self) -> str:
        self.validate()
        return _sha256_json(self.payload())

    def payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["methods"] = list(self.methods)
        payload["decoding"] = dict(self.decoding)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "config_hash": self.config_hash,
            "config": self.payload(),
        }


class JsonlCheckpoint:
    """Append one complete method-case result per durable JSONL row."""

    def __init__(self, results_path: Path, config: RunConfig) -> None:
        self.results_path = results_path
        self.config_path = results_path.with_suffix(
            results_path.suffix + ".config.json"
        )
        self.config = config
        self._initialized = False
        self._completed_keys: set[str] = set()

    def initialize(self) -> None:
        if self._initialized:
            return
        self.config.validate()
        self.results_path.parent.mkdir(parents=True, exist_ok=True)
        if self.results_path.exists() and not self.config_path.exists():
            raise ValueError("results exist without a run-config sidecar")
        if self.config_path.exists():
            stored = _read_json_object(self.config_path)
            if stored != self.config.to_dict():
                raise ValueError("incompatible resume: run-config hash differs")
        else:
            _atomic_write_json(self.config_path, self.config.to_dict())
        if not self.results_path.exists():
            self.results_path.touch()
        rows = self._read_rows()
        self._completed_keys = {str(row["result_key"]) for row in rows}
        self._initialized = True

    def load_rows(self) -> list[dict[str, Any]]:
        self.initialize()
        rows = self._read_rows()
        self._completed_keys = {str(row["result_key"]) for row in rows}
        return rows

    def _read_rows(self) -> list[dict[str, Any]]:
        if not self.results_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        keys: set[str] = set()
        for line_number, line in enumerate(
            self.results_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not line.strip():
                raise ValueError(f"blank checkpoint row at line {line_number}")
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"invalid checkpoint JSON at line {line_number}: {error.msg}"
                ) from error
            self._validate_row(row, line_number=line_number)
            key = str(row["result_key"])
            if key in keys:
                raise ValueError(f"duplicate checkpoint result key: {key}")
            keys.add(key)
            rows.append(row)
        return rows

    def completed_keys(self) -> set[str]:
        self.initialize()
        return set(self._completed_keys)

    def append(self, result: MethodCaseResult) -> dict[str, Any]:
        self.initialize()
        key = result_key(result.case_id, result.method_id)
        if key in self._completed_keys:
            raise ValueError(f"checkpoint already contains result: {key}")
        if result.method_id not in self.config.methods:
            raise ValueError("result method is absent from run config")
        row = {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "config_hash": self.config.config_hash,
            "result_key": key,
            "case_id": result.case_id,
            "method_id": result.method_id,
            "model_id": self.config.model_id,
            "model_revision": self.config.model_revision,
            "result": result.to_dict(),
        }
        encoded = _canonical_json(row) + "\n"
        with self.results_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        self._completed_keys.add(key)
        return row

    def assert_complete(self, expected_keys: Iterable[str]) -> None:
        expected = set(expected_keys)
        actual = self.completed_keys()
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        if missing or unexpected:
            raise ValueError(
                f"checkpoint matrix mismatch; missing={missing}, "
                f"unexpected={unexpected}"
            )

    def _validate_row(self, row: Any, *, line_number: int) -> None:
        fields = {
            "schema_version",
            "config_hash",
            "result_key",
            "case_id",
            "method_id",
            "model_id",
            "model_revision",
            "result",
        }
        if not isinstance(row, Mapping) or set(row) != fields:
            raise ValueError(f"checkpoint schema mismatch at line {line_number}")
        if row["schema_version"] != CHECKPOINT_SCHEMA_VERSION:
            raise ValueError(f"checkpoint version mismatch at line {line_number}")
        if row["config_hash"] != self.config.config_hash:
            raise ValueError(f"incompatible resume row at line {line_number}")
        if row["model_id"] != self.config.model_id:
            raise ValueError(f"model id mismatch at line {line_number}")
        if row["model_revision"] != self.config.model_revision:
            raise ValueError(f"model revision mismatch at line {line_number}")
        expected_key = result_key(str(row["case_id"]), str(row["method_id"]))
        if row["result_key"] != expected_key:
            raise ValueError(f"result key mismatch at line {line_number}")
        result = row["result"]
        if not isinstance(result, Mapping):
            raise ValueError(f"result payload is not an object at line {line_number}")
        if result.get("case_id") != row["case_id"]:
            raise ValueError(f"nested case id mismatch at line {line_number}")
        if result.get("method_id") != row["method_id"]:
            raise ValueError(f"nested method id mismatch at line {line_number}")


def expected_result_keys(
    case_ids: Iterable[str],
    methods: Iterable[str],
) -> tuple[str, ...]:
    return tuple(
        result_key(case_id, method_id)
        for case_id in case_ids
        for method_id in methods
    )


def result_key(case_id: str, method_id: str) -> str:
    if not case_id or "\0" in case_id or not method_id or "\0" in method_id:
        raise ValueError("case_id and method_id must be non-empty and contain no NUL")
    return hashlib.sha256(
        f"{case_id}\0{method_id}".encode("utf-8")
    ).hexdigest()


def create_compact_checkpoint_zip(
    checkpoint: JsonlCheckpoint,
    output_path: Path,
) -> dict[str, Any]:
    """Create a deterministic compact archive with file checksums."""

    checkpoint.initialize()
    rows = checkpoint.load_rows()
    files = {
        "run_config.json": checkpoint.config_path.read_bytes(),
        "results.jsonl": checkpoint.results_path.read_bytes(),
    }
    manifest = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "config_hash": checkpoint.config.config_hash,
        "row_count": len(rows),
        "files": {
            name: {
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
            for name, content in sorted(files.items())
        },
    }
    files["manifest.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with zipfile.ZipFile(
        temp_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)
    temp_path.replace(output_path)
    return {
        **manifest,
        "archive_path": output_path.as_posix(),
        "archive_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
    }


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
