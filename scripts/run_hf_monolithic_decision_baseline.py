"""Run a frozen Hugging Face monolithic decision baseline on a CUDA GPU."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
import sys
from time import perf_counter
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.monolithic_decision import (  # noqa: E402
    PROMPT_VERSION,
    parse_model_response,
    validate_input_record,
)


DEFAULT_INPUTS = ROOT / "outputs" / "evaluations" / "week9_monolithic_diagnostic_inputs_v1.jsonl"
DEFAULT_OUTPUT = ROOT / "outputs" / "evaluations" / "week9_monolithic_qwen25_7b_raw_v1.json"
DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--revision",
        default=None,
        help="Optional exact Hugging Face commit. When omitted, the runner resolves and pins the current commit.",
    )
    parser.add_argument("--precision", choices=("4bit", "float16"), default="4bit")
    parser.add_argument("--max-new-tokens", type=int, default=192)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--required-device-substring", default="T4")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _validate_args(args)
    input_rows = _read_jsonl(args.inputs)
    for row in input_rows:
        validate_input_record(row)
        if row.get("prompt_version") != PROMPT_VERSION:
            raise ValueError(
                f"{row.get('case_id')}: unsupported prompt version "
                f"{row.get('prompt_version')!r}"
            )

    try:
        import torch
        from huggingface_hub import HfApi
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
        )
    except ImportError as error:
        raise RuntimeError(
            "Install the Colab baseline dependencies: transformers, accelerate, "
            "bitsandbytes, huggingface_hub, and torch."
        ) from error

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required; do not run this baseline on local CPU")
    device_name = torch.cuda.get_device_name(0)
    if (
        args.required_device_substring
        and args.required_device_substring.lower() not in device_name.lower()
    ):
        raise RuntimeError(
            f"required device containing {args.required_device_substring!r}; "
            f"found {device_name!r}"
        )

    model_info = HfApi().model_info(args.model, revision=args.revision or "main")
    resolved_revision = str(model_info.sha)
    model_license = _model_license(model_info)
    generation_parameters = {
        "max_new_tokens": args.max_new_tokens,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "do_sample": args.temperature > 0,
        "repetitions": args.repetitions,
        "base_seed": args.seed,
    }
    run_identity = {
        "model": args.model,
        "model_revision": resolved_revision,
        "precision": args.precision,
        "prompt_version": PROMPT_VERSION,
        "input_sha256": _sha256(args.inputs),
        "generation_parameters": generation_parameters,
    }
    payload = _initial_or_resumed_payload(
        args.output,
        resume=args.resume,
        run_identity=run_identity,
        input_path=args.inputs,
        device_name=device_name,
        model_license=model_license,
    )
    completed = {
        (str(row["case_id"]), int(row["repetition"]))
        for row in payload.get("records", [])
    }

    tokenizer = AutoTokenizer.from_pretrained(
        args.model,
        revision=resolved_revision,
        trust_remote_code=False,
    )
    load_started = perf_counter()
    model_kwargs: dict[str, Any] = {
        "revision": resolved_revision,
        "device_map": "auto",
        "trust_remote_code": False,
        "torch_dtype": torch.float16,
    }
    if args.precision == "4bit":
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
    model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)
    model.eval()
    payload["metadata"]["model_load_elapsed_seconds"] = perf_counter() - load_started
    _write_json(payload, args.output)

    for input_row in input_rows:
        for repetition in range(args.repetitions):
            key = (str(input_row["case_id"]), repetition)
            if key in completed:
                continue
            seed = args.seed + repetition
            torch.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
            encoded = tokenizer.apply_chat_template(
                input_row["messages"],
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
                return_dict=True,
            )
            encoded = encoded.to(model.device)
            generation_kwargs: dict[str, Any] = {
                "max_new_tokens": args.max_new_tokens,
                "do_sample": args.temperature > 0,
                "pad_token_id": tokenizer.eos_token_id,
            }
            if args.temperature > 0:
                generation_kwargs.update(
                    {"temperature": args.temperature, "top_p": args.top_p}
                )
            started = perf_counter()
            with torch.inference_mode():
                generated = model.generate(**encoded, **generation_kwargs)
            elapsed = perf_counter() - started
            prompt_tokens = int(encoded["input_ids"].shape[-1])
            generated_tokens = generated[0][prompt_tokens:]
            raw_response = tokenizer.decode(
                generated_tokens,
                skip_special_tokens=True,
            ).strip()
            parsed = parse_model_response(raw_response)
            payload["records"].append(
                {
                    "case_id": str(input_row["case_id"]),
                    "stratum": str(input_row["stratum"]),
                    "repetition": repetition,
                    "seed": seed,
                    "prompt_sha256": str(input_row["prompt_sha256"]),
                    "prompt_tokens": prompt_tokens,
                    "generated_tokens": int(generated_tokens.shape[-1]),
                    "generation_elapsed_seconds": elapsed,
                    "raw_response": raw_response,
                    "parsed_response": parsed,
                }
            )
            payload["metadata"]["status"] = "running"
            payload["metadata"]["records_completed"] = len(payload["records"])
            _write_json(payload, args.output)

    payload["metadata"]["status"] = "completed"
    payload["metadata"]["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    payload["metadata"]["records_completed"] = len(payload["records"])
    payload["metadata"]["valid_response_count"] = sum(
        row["parsed_response"]["valid"] for row in payload["records"]
    )
    payload["metadata"]["invalid_response_count"] = (
        len(payload["records"]) - payload["metadata"]["valid_response_count"]
    )
    _write_json(payload, args.output)
    print(
        json.dumps(
            {
                "status": payload["metadata"]["status"],
                "model": args.model,
                "model_revision": resolved_revision,
                "device": device_name,
                "records": len(payload["records"]),
                "valid_responses": payload["metadata"]["valid_response_count"],
                "output": str(args.output),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _validate_args(args: argparse.Namespace) -> None:
    if args.max_new_tokens <= 0:
        raise ValueError("--max-new-tokens must be positive")
    if args.repetitions <= 0:
        raise ValueError("--repetitions must be positive")
    if args.temperature < 0:
        raise ValueError("--temperature cannot be negative")
    if not 0 < args.top_p <= 1:
        raise ValueError("--top-p must be within (0, 1]")
    if args.output.exists() and not args.resume:
        raise FileExistsError(
            f"output already exists: {args.output}; use --resume or a new output path"
        )


def _initial_or_resumed_payload(
    output: Path,
    *,
    resume: bool,
    run_identity: dict[str, Any],
    input_path: Path,
    device_name: str,
    model_license: str,
) -> dict[str, Any]:
    if resume and output.exists():
        payload = _read_json(output)
        for field, expected in run_identity.items():
            actual = payload.get("metadata", {}).get(field)
            if actual != expected:
                raise ValueError(
                    f"cannot resume: metadata {field!r} is {actual!r}, expected {expected!r}"
                )
        return payload
    return {
        "metadata": {
            "status": "initializing",
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            **run_identity,
            "model_license": model_license,
            "input_path": _repo_path(input_path),
            "device": device_name,
            "python_version": platform.python_version(),
            "package_versions": {
                name: _package_version(name)
                for name in (
                    "torch",
                    "transformers",
                    "accelerate",
                    "bitsandbytes",
                    "huggingface_hub",
                )
            },
            "trust_remote_code": False,
            "gold_labels_loaded": False,
            "research_note": (
                "Frozen same-input monolithic decision baseline. Raw responses and "
                "parse failures are preserved without correction."
            ),
        },
        "records": [],
    }


def _model_license(model_info: Any) -> str:
    card_data = getattr(model_info, "card_data", None)
    if card_data is None:
        return "not stated"
    if hasattr(card_data, "to_dict"):
        payload = card_data.to_dict()
    elif isinstance(card_data, dict):
        payload = card_data
    else:
        return "not stated"
    return str(payload.get("license") or "not stated")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON input must contain an object: {path}")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"JSONL input must contain objects: {path}")
    ids = [str(row.get("case_id")) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("input case IDs must be unique")
    return rows


def _write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not installed"


def _repo_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return str(resolved)


if __name__ == "__main__":
    main()
