import copy
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any, Dict


DEFAULT_SIGNING_KEY_FILE = ".shepherd/signing.key"
TOP_LEVEL_SIGNATURE_KEYS = {
    "mission_digest",
    "evidence_digest",
    "signature",
    "record_signature",
    "verification",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _strip_keys_recursive(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_keys_recursive(item, keys)
            for key, item in value.items()
            if key not in keys
        }
    if isinstance(value, list):
        return [_strip_keys_recursive(item, keys) for item in value]
    return value


def digest_payload(payload: Dict, *, recursive_signature_fields: bool = False) -> str:
    unsigned = {
        key: value
        for key, value in payload.items()
        if key not in TOP_LEVEL_SIGNATURE_KEYS
    }
    if recursive_signature_fields:
        unsigned = _strip_keys_recursive(unsigned, {"signature"})
    return hashlib.sha256(_canonical_json(unsigned).encode("utf-8")).hexdigest()


class SignatureManager:
    def __init__(self, key: str | None = None, key_file: str | Path | None = None):
        self._key_override = key
        self.key_file = Path(key_file or os.environ.get("SHEPHERD_SIGNING_KEY_FILE", DEFAULT_SIGNING_KEY_FILE))
        self._key = None

    def _load_key(self) -> bytes:
        if self._key is not None:
            return self._key

        key = self._key_override or os.environ.get("SHEPHERD_SIGNING_KEY")
        if not key:
            self.key_file.parent.mkdir(parents=True, exist_ok=True)
            if not self.key_file.exists():
                self.key_file.write_text(secrets.token_hex(32), encoding="utf-8")
            key = self.key_file.read_text(encoding="utf-8").strip()

        self._key = key.encode("utf-8")
        return self._key

    def key_id(self) -> str:
        return hashlib.sha256(self._load_key()).hexdigest()[:16]

    def sign_digest(self, payload_digest: str, payload_type: str) -> Dict:
        signature = hmac.new(self._load_key(), payload_digest.encode("utf-8"), hashlib.sha256).hexdigest()
        return {
            "algorithm": "HMAC-SHA256",
            "key_id": self.key_id(),
            "payload_type": payload_type,
            "payload_digest": payload_digest,
            "signature": signature,
            "signed_at": time.time(),
        }

    def sign_payload(
        self,
        payload: Dict,
        payload_type: str,
        digest_field: str,
        signature_field: str,
        recursive_signature_fields: bool = False,
    ) -> Dict:
        signed = copy.deepcopy(payload)
        payload_digest = digest_payload(signed, recursive_signature_fields=recursive_signature_fields)
        signed[digest_field] = payload_digest
        signed[signature_field] = self.sign_digest(payload_digest, payload_type)
        return signed

    def verify_payload(
        self,
        payload: Dict,
        digest_field: str,
        signature_field: str,
        recursive_signature_fields: bool = False,
    ) -> Dict:
        expected_digest = digest_payload(payload, recursive_signature_fields=recursive_signature_fields)
        signature = payload.get(signature_field) or {}
        recorded_digest = payload.get(digest_field)
        recorded_signature = signature.get("signature")
        expected_signature = None
        if recorded_digest:
            expected_signature = hmac.new(
                self._load_key(),
                str(recorded_digest).encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

        return {
            "digest_valid": bool(recorded_digest) and hmac.compare_digest(str(recorded_digest), expected_digest),
            "signature_valid": bool(recorded_signature and expected_signature) and hmac.compare_digest(
                str(recorded_signature),
                expected_signature,
            ),
            "expected_digest": expected_digest,
            "recorded_digest": recorded_digest,
            "key_id": signature.get("key_id"),
            "algorithm": signature.get("algorithm"),
        }


default_signature_manager = SignatureManager()
