import argparse
import asyncio
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Dict, Iterable, List

try:
    from backend.brain import MissionParser
    from backend.controller import SwarmManager
    from backend.evidence_log import EvidenceLogger
    from backend.parser_promotion import TRANSFORMER_MODEL_CANDIDATE
    from backend.parser_runtime import ENABLE_ENV, MODEL_DIR_ENV, PROMOTION_REPORT_ENV, RUNTIME_ENV, SHADOW_ENV
    from backend.parser_shadow_candidates import generate_parser_shadow_candidates, write_candidates_jsonl
    from backend.parser_shadow_report import generate_parser_shadow_report, write_parser_shadow_report
except ImportError:
    from brain import MissionParser
    from controller import SwarmManager
    from evidence_log import EvidenceLogger
    from parser_promotion import TRANSFORMER_MODEL_CANDIDATE
    from parser_runtime import ENABLE_ENV, MODEL_DIR_ENV, PROMOTION_REPORT_ENV, RUNTIME_ENV, SHADOW_ENV
    from parser_shadow_candidates import generate_parser_shadow_candidates, write_candidates_jsonl
    from parser_shadow_report import generate_parser_shadow_report, write_parser_shadow_report


CAPTURE_SCHEMA = "shepherd-parser-shadow-capture/1.0"
DEFAULT_EVIDENCE_DIR = Path(".tmp_scenarios/parser-shadow-evidence")
DEFAULT_CAPTURE_REPORT_PATH = Path(".tmp_scenarios/parser-shadow-capture.json")
DEFAULT_SHADOW_REPORT_PATH = Path(".tmp_scenarios/parser-shadow-report.json")
DEFAULT_CANDIDATES_PATH = Path(".tmp_scenarios/parser-shadow-candidates.jsonl")

DEFAULT_COMMANDS = [
    "Urgent: perform a spiral scan at Al Nada with five drones.",
    "Secure the National Museum with two drones.",
    "Send four drones to KAFD for a lawn mower sweep.",
    "RTB all units to base.",
    "Do not send any drones to KAFD.",
    "Send a pair to KAFD, but keep one here.",
    "Have alpha and beta inspect Al Nada together.",
    "Send two drones and recall them immediately.",
    "Dispatch three drones near Wadi Hanifah and keep perimeter spacing.",
    "Move alpha-1 and alpha-2 to the Ministry of Defense.",
    "Search the Boulevard with six drones in a widening spiral.",
    "Send two drones to 24.8012, 46.6808.",
]


def discover_promoted_transformer(
    search_root: str | Path = ".tmp_models",
) -> Dict[str, str] | None:
    """Find the newest local promoted transformer report and model directory."""
    root = Path(search_root)
    if not root.exists():
        return None

    matches = []
    for path in root.rglob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as handle:
                report = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if report.get("candidate_type") != TRANSFORMER_MODEL_CANDIDATE or report.get("promoted") is not True:
            continue
        candidate_path = report.get("candidate_path")
        if not candidate_path:
            continue
        model_dir = Path(candidate_path)
        if not model_dir.is_absolute():
            model_dir = (Path.cwd() / model_dir).resolve()
        if not (model_dir / "shepherd_model_contract.json").exists():
            continue
        matches.append((path.stat().st_mtime, path, model_dir))

    if not matches:
        return None
    _, report_path, model_dir = sorted(matches, key=lambda item: item[0], reverse=True)[0]
    return {"model_dir": str(model_dir), "promotion_report": str(report_path)}


async def capture_parser_shadow_evidence(
    *,
    commands: Iterable[str] | None = None,
    evidence_dir: str | Path = DEFAULT_EVIDENCE_DIR,
    model_dir: str | Path | None = None,
    promotion_report: str | Path | None = None,
    capture_report_path: str | Path | None = DEFAULT_CAPTURE_REPORT_PATH,
    shadow_report_path: str | Path | None = DEFAULT_SHADOW_REPORT_PATH,
    candidates_path: str | Path | None = DEFAULT_CANDIDATES_PATH,
    include_matches: bool = False,
    limit: int = 100,
    allow_llm_active: bool = False,
    require_disagreements: bool = False,
    backend_main=None,
    parser_factory: Callable[[], MissionParser] | None = None,
) -> Dict:
    """Run real plan/confirm flow with a promoted parser in report-only shadow mode."""
    selected_commands = [command.strip() for command in (commands or DEFAULT_COMMANDS) if command and command.strip()]
    if not selected_commands:
        raise ValueError("At least one command is required for parser shadow capture")

    resolved = _resolve_shadow_candidate(model_dir, promotion_report)
    env_updates = {
        ENABLE_ENV: "",
        RUNTIME_ENV: "",
        SHADOW_ENV: "1",
    }
    if resolved.get("model_dir"):
        env_updates[MODEL_DIR_ENV] = resolved["model_dir"]
    if resolved.get("promotion_report"):
        env_updates[PROMOTION_REPORT_ENV] = resolved["promotion_report"]

    with _temporary_env(env_updates):
        if backend_main is None:
            from backend import main as backend_main
        result = await _capture_with_backend(
            backend_main,
            selected_commands,
            evidence_dir=Path(evidence_dir),
            parser_factory=parser_factory,
            allow_llm_active=allow_llm_active,
        )

    logger = EvidenceLogger(evidence_dir)
    shadow_report = generate_parser_shadow_report(
        evidence_logger=logger,
        limit=limit,
        include_records=True,
    )
    candidates = generate_parser_shadow_candidates(
        evidence_logger=logger,
        limit=limit,
        include_matches=include_matches,
    )

    if shadow_report_path:
        shadow_report["report_path"] = write_parser_shadow_report(shadow_report, shadow_report_path)
    if candidates_path:
        candidates["output_path"] = write_candidates_jsonl(candidates, candidates_path)

    summary = {
        "commands_requested": len(selected_commands),
        "missions_confirmed": sum(1 for item in result["missions"] if item.get("confirmed")),
        "evidence_records": len(result["evidence_ids"]),
        "shadow_audits": shadow_report["summary"].get("audit_count", 0),
        "shadow_mismatches": shadow_report["summary"].get("mismatch_count", 0),
        "shadow_failures": shadow_report["summary"].get("failed_audit_count", 0),
        "candidate_count": candidates["summary"].get("candidate_count", 0),
    }
    capture = {
        "schema": CAPTURE_SCHEMA,
        "captured_at": time.time(),
        "evidence_dir": str(Path(evidence_dir)),
        "shadow_candidate": {
            "model_dir": resolved.get("model_dir"),
            "promotion_report": resolved.get("promotion_report"),
            "auto_discovered": bool(resolved.get("auto_discovered")),
        },
        "validation_scope": {
            "normal_mission_planning": True,
            "mission_confirmation_path": True,
            "shadow_mode_report_only": True,
            "active_parser_switched": False,
            "mavsdk_dispatch": False,
            "live_mode_forced_off": True,
            "independent_scenario_fleet_reset": True,
        },
        "summary": summary,
        "missions": result["missions"],
        "parser_shadow_report": shadow_report,
        "parser_shadow_candidates": candidates,
    }
    if capture_report_path:
        capture["capture_report_path"] = _write_json(capture, capture_report_path)

    if require_disagreements and summary["candidate_count"] == 0:
        raise RuntimeError("Parser shadow capture completed but produced no disagreement candidates")
    return capture


async def _capture_with_backend(
    backend_main,
    commands: List[str],
    *,
    evidence_dir: Path,
    parser_factory: Callable[[], MissionParser] | None,
    allow_llm_active: bool,
) -> Dict:
    old_logger = backend_main.evidence_logger
    old_parser = backend_main.parser
    old_swarm = backend_main.swarm
    old_pending = dict(backend_main.PENDING_MISSION_PLANS)
    old_operator = dict(backend_main.OPERATOR_STATE)

    try:
        backend_main.evidence_logger = EvidenceLogger(evidence_dir)
        backend_main.parser = parser_factory() if parser_factory else MissionParser()
        if not allow_llm_active:
            backend_main.parser._ollama_available = False
        backend_main.swarm = SwarmManager()
        backend_main.swarm.live_mode = False
        backend_main.PENDING_MISSION_PLANS.clear()
        backend_main.OPERATOR_STATE.update(
            {
                "active": True,
                "operator_lat": 24.7136,
                "operator_lon": 46.6753,
                "operator_heading": 0.0,
                "accuracy_m": 8.0,
                "heading_source": "parser_shadow_capture",
                "updated_at": time.time(),
            }
        )

        missions = []
        evidence_ids = []
        for command in commands:
            backend_main.swarm = SwarmManager()
            backend_main.swarm.live_mode = False
            backend_main.PENDING_MISSION_PLANS.clear()
            mission = await _capture_one_mission(backend_main, command)
            missions.append(mission)
            if mission.get("evidence_id"):
                evidence_ids.append(mission["evidence_id"])
        return {"missions": missions, "evidence_ids": evidence_ids}
    finally:
        backend_main.evidence_logger = old_logger
        backend_main.parser = old_parser
        backend_main.swarm = old_swarm
        backend_main.PENDING_MISSION_PLANS.clear()
        backend_main.PENDING_MISSION_PLANS.update(old_pending)
        backend_main.OPERATOR_STATE.clear()
        backend_main.OPERATOR_STATE.update(old_operator)


async def _capture_one_mission(backend_main, command: str) -> Dict:
    mission = {
        "command": command,
        "planned": False,
        "confirmed": False,
        "confirmable": False,
        "evidence_id": None,
        "shadow_audit_count": 0,
        "shadow_mismatch_count": 0,
    }
    try:
        plan = await backend_main.create_mission_plan(
            backend_main.CommandInput(command=command, selected_drones=[])
        )
        mission.update(
            {
                "planned": True,
                "plan_id": plan.get("plan_id"),
                "status": plan.get("status"),
                "confirmable": bool(plan.get("plan_summary", {}).get("confirmable")),
                "assigned": plan.get("assigned", []),
                "plan_summary": plan.get("plan_summary", {}),
            }
        )
        if not mission["confirmable"]:
            mission["error"] = "Mission plan was not confirmable; no evidence record written."
            return mission

        confirmed = await backend_main.confirm_mission_plan(
            backend_main.MissionPlanRef(plan_id=plan["plan_id"])
        )
        evidence = confirmed.get("evidence") or {}
        audits = confirmed.get("parser_summary", {}).get("parser_shadow_audits", []) or []
        mission.update(
            {
                "confirmed": bool(confirmed.get("confirmed")),
                "status": confirmed.get("status"),
                "assigned": confirmed.get("assigned", []),
                "evidence_id": evidence.get("evidence_id"),
                "evidence_path": evidence.get("path"),
                "shadow_audit_count": len(audits),
                "shadow_mismatch_count": sum(
                    1 for audit in audits if audit.get("status") == "compared" and not audit.get("matches_active")
                ),
                "shadow_failure_count": sum(1 for audit in audits if audit.get("status") == "failed"),
            }
        )
    except Exception as exc:
        mission["error"] = str(exc)
        mission["error_type"] = type(exc).__name__
    return mission


def _resolve_shadow_candidate(model_dir: str | Path | None, promotion_report: str | Path | None) -> Dict[str, str | bool | None]:
    resolved = {
        "model_dir": str(model_dir) if model_dir else os.environ.get(MODEL_DIR_ENV),
        "promotion_report": str(promotion_report) if promotion_report else os.environ.get(PROMOTION_REPORT_ENV),
        "auto_discovered": False,
    }
    if resolved["model_dir"] and resolved["promotion_report"]:
        return resolved

    discovered = discover_promoted_transformer()
    if discovered:
        resolved["model_dir"] = resolved["model_dir"] or discovered["model_dir"]
        resolved["promotion_report"] = resolved["promotion_report"] or discovered["promotion_report"]
        resolved["auto_discovered"] = True
    return resolved


def _read_commands_file(path: str | Path) -> List[str]:
    commands = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("{"):
                payload = json.loads(stripped)
                stripped = payload.get("command", "")
            commands.append(stripped)
    return commands


@contextmanager
def _temporary_env(updates: Dict[str, str | None]):
    previous = {key: os.environ.get(key) for key in updates}
    try:
        for key, value in updates.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(value)
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _write_json(payload: Dict, path: str | Path) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    return str(target)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture signed parser-shadow evidence by running normal Shepherd-AI mission plan/confirm flow."
    )
    parser.add_argument("--command", action="append", default=[], help="Mission command to capture. Repeatable.")
    parser.add_argument("--commands-file", default=None, help="Optional text/JSONL command file. One command per line.")
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR), help="Ignored evidence output directory.")
    parser.add_argument("--model-dir", default=None, help="Promoted transformer model directory.")
    parser.add_argument("--promotion-report", default=None, help="Promotion report for the transformer model.")
    parser.add_argument("--capture-report", default=str(DEFAULT_CAPTURE_REPORT_PATH), help="JSON capture report path.")
    parser.add_argument("--shadow-report", default=str(DEFAULT_SHADOW_REPORT_PATH), help="JSON shadow report path.")
    parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES_PATH), help="JSONL disagreement candidate path.")
    parser.add_argument("--include-matches", action="store_true", help="Export matching comparisons as candidates too.")
    parser.add_argument("--allow-llm-active", action="store_true", help="Allow Ollama/LLM as the active parser.")
    parser.add_argument("--require-disagreements", action="store_true", help="Exit nonzero if no candidates are produced.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum evidence records to summarize.")
    parser.add_argument("--summary-only", action="store_true", help="Omit full records/candidates from stdout.")
    args = parser.parse_args()

    commands = list(args.command)
    if args.commands_file:
        commands.extend(_read_commands_file(args.commands_file))
    if not commands:
        commands = DEFAULT_COMMANDS

    try:
        result = asyncio.run(
            capture_parser_shadow_evidence(
                commands=commands,
                evidence_dir=args.evidence_dir,
                model_dir=args.model_dir,
                promotion_report=args.promotion_report,
                capture_report_path=args.capture_report,
                shadow_report_path=args.shadow_report,
                candidates_path=args.candidates,
                include_matches=args.include_matches,
                allow_llm_active=args.allow_llm_active,
                require_disagreements=args.require_disagreements,
                limit=args.limit,
            )
        )
    except Exception as exc:
        print(json.dumps({"error": str(exc), "error_type": type(exc).__name__}, indent=2, sort_keys=True))
        return 1

    rendered = dict(result)
    if args.summary_only:
        rendered["missions"] = []
        rendered["parser_shadow_report"] = {
            **rendered["parser_shadow_report"],
            "records": [],
        }
        rendered["parser_shadow_candidates"] = {
            **rendered["parser_shadow_candidates"],
            "candidates": [],
        }
    print(json.dumps(rendered, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
