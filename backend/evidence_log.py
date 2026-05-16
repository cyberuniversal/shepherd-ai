import json
import os
import time
import uuid
from pathlib import Path
from typing import Dict, List

try:
    from backend.signing import SignatureManager, default_signature_manager
except ImportError:
    from signing import SignatureManager, default_signature_manager


DEFAULT_EVIDENCE_DIR = "evidence"


class EvidenceLogger:
    def __init__(self, root_dir: str | Path | None = None, signer: SignatureManager | None = None):
        self.root_dir = Path(root_dir or os.environ.get("SHEPHERD_EVIDENCE_DIR", DEFAULT_EVIDENCE_DIR))
        self.signer = signer or default_signature_manager

    def _ensure_root(self):
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _record_path(self, evidence_id: str) -> Path:
        if not evidence_id.startswith("evidence-") or "/" in evidence_id or "\\" in evidence_id:
            raise FileNotFoundError(evidence_id)
        return self.root_dir / f"{evidence_id}.json"

    def record_confirmed_mission(self, plan: Dict, response: Dict, operator_state: Dict | None = None) -> Dict:
        self._ensure_root()
        now = time.time()
        evidence_id = f"evidence-{uuid.uuid4().hex[:12]}"
        mission_programs = response.get("mission_programs", [])
        mission_digests = [
            program.get("mission_digest")
            for program in mission_programs
            if program.get("mission_digest")
        ]
        preflight_results = [
            result.get("preflight")
            for result in response.get("execution_results", [])
            if result.get("preflight")
        ]

        record = {
            "evidence_id": evidence_id,
            "record_type": "confirmed_mission",
            "recorded_at": now,
            "plan_id": response.get("plan_id") or plan.get("plan_id"),
            "command": plan.get("command"),
            "confirmation": {
                "confirmed": bool(response.get("confirmed")),
                "confirmed_at": now,
                "preview_created_at": plan.get("created_at"),
                "operator_state": operator_state or {},
            },
            "selected_drones": response.get("assigned", []),
            "intents": response.get("intents", []),
            "target_resolution": response.get("target_resolution", []),
            "parser_summary": response.get("parser_summary", {}),
            "mission_digests": mission_digests,
            "mission_programs": mission_programs,
            "safety_reports": response.get("safety_reports", []),
            "preflight_results": preflight_results,
            "execution_results": response.get("execution_results", []),
            "action_script_summaries": [
                {
                    "script_id": script.get("script_id"),
                    "language": script.get("language"),
                    "generated_at": script.get("generated_at"),
                    "sandbox": script.get("sandbox"),
                    "sensor_events": script.get("sensor_events", []),
                    "route_patches": script.get("route_patches", []),
                }
                for script in response.get("action_scripts", [])
            ],
            "plan_summary": response.get("plan_summary", {}),
            "status": response.get("status"),
            "message": response.get("message"),
        }
        record = self.signer.sign_payload(
            record,
            payload_type="mission_evidence_record",
            digest_field="evidence_digest",
            signature_field="record_signature",
        )

        path = self._record_path(evidence_id)
        tmp_path = path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, sort_keys=True)
            handle.write("\n")
        tmp_path.replace(path)

        return {
            "recorded": True,
            "evidence_id": evidence_id,
            "path": str(path),
            "mission_digests": mission_digests,
            "recorded_at": now,
            "evidence_digest": record["evidence_digest"],
            "record_signature": record["record_signature"],
        }

    def read_record(self, evidence_id: str) -> Dict:
        path = self._record_path(evidence_id)
        with path.open("r", encoding="utf-8") as handle:
            record = json.load(handle)
        record["verification"] = self.verify_record(record)
        return record

    def verify_record(self, record_or_id: Dict | str) -> Dict:
        if isinstance(record_or_id, str):
            path = self._record_path(record_or_id)
            with path.open("r", encoding="utf-8") as handle:
                record = json.load(handle)
        else:
            record = record_or_id
        return self.signer.verify_payload(record, "evidence_digest", "record_signature")

    def list_records(self, limit: int = 25) -> List[Dict]:
        self._ensure_root()
        records = []
        for path in sorted(self.root_dir.glob("evidence-*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                with path.open("r", encoding="utf-8") as handle:
                    record = json.load(handle)
            except (OSError, json.JSONDecodeError):
                continue
            verification = self.verify_record(record)
            records.append({
                "evidence_id": record.get("evidence_id"),
                "recorded_at": record.get("recorded_at"),
                "plan_id": record.get("plan_id"),
                "command": record.get("command"),
                "selected_drones": record.get("selected_drones", []),
                "mission_digests": record.get("mission_digests", []),
                "evidence_digest": record.get("evidence_digest"),
                "digest_valid": verification.get("digest_valid"),
                "signature_valid": verification.get("signature_valid"),
                "verified": bool(verification.get("digest_valid") and verification.get("signature_valid")),
                "status": record.get("status"),
            })
            if len(records) >= limit:
                break
        return records
