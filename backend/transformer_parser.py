import argparse
import json
import inspect
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Dict, Iterable, List

try:
    from backend.learned_parser import (
        BOUNDED_OUTPUT_FIELDS,
        coerce_bounded_intent,
        load_frozen_splits,
    )
    from backend.mission_dataset import (
        DEFAULT_ADVERSARIAL_PATH,
        DEFAULT_AUGMENTATION_PATH,
        DEFAULT_BENCHMARK_PATH,
        EVALUATED_INTENT_FIELDS,
    )
except ImportError:
    from learned_parser import BOUNDED_OUTPUT_FIELDS, coerce_bounded_intent, load_frozen_splits
    from mission_dataset import DEFAULT_ADVERSARIAL_PATH, DEFAULT_AUGMENTATION_PATH, DEFAULT_BENCHMARK_PATH, EVALUATED_INTENT_FIELDS


TRANSFORMER_CORPUS_SCHEMA = "shepherd-transformer-parser-corpus/1.0"
TRANSFORMER_MODEL_CONTRACT_SCHEMA = "shepherd-transformer-parser-contract/1.0"
TRANSFORMER_DIAGNOSTIC_SCHEMA = "shepherd-transformer-generation-diagnostics/1.0"
DEFAULT_TRANSFORMER_CORPUS_DIR = Path(".tmp_models/transformer_parser/corpus")
DEFAULT_TRANSFORMER_MODEL_DIR = Path(".tmp_models/transformer_parser/model")
DEFAULT_BASE_MODEL = "google/mt5-small"
DEFAULT_MAX_SOURCE_LENGTH = 160
DEFAULT_MAX_TARGET_LENGTH = 320
TASK_PREFIX = "Extract Shepherd-AI bounded intent JSON from command: "


def write_training_corpus(
    output_dir: str | Path = DEFAULT_TRANSFORMER_CORPUS_DIR,
    *,
    dataset_path: str | Path = DEFAULT_BENCHMARK_PATH,
    augmentation_path: str | Path | None = None,
    adversarial_path: str | Path | None = DEFAULT_ADVERSARIAL_PATH,
) -> Dict:
    splits = load_frozen_splits(dataset_path, augmentation_path=augmentation_path, adversarial_path=adversarial_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    split_files = {}
    split_summaries = {}
    for split_name, examples in splits.items():
        records = [_training_record(example, split_name) for example in examples]
        file_path = output_path / f"{split_name}.jsonl"
        _write_jsonl(records, file_path)
        split_files[split_name] = str(file_path)
        split_summaries[split_name] = {
            "count": len(records),
            "used_for_training": split_name == "train" or (split_name == "augmentation" and bool(records)),
            "languages": _language_counts(records),
            "source_ids": [record["id"] for record in records],
        }

    manifest = {
        "schema": TRANSFORMER_CORPUS_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "path": str(Path(dataset_path)),
            "augmentation_path": str(Path(augmentation_path)) if augmentation_path else None,
            "adversarial_path": str(Path(adversarial_path)) if adversarial_path else None,
        },
        "contract": {
            "input": "operator_command_text",
            "target": "bounded_intent_and_constraints_json",
            "output": "bounded_intent_json_only",
            "dispatch_authority": False,
            "confirmation_required": True,
            "deterministic_backend_required": True,
        },
        "splits": split_summaries,
        "files": split_files,
    }
    manifest["corpus_digest"] = _digest_payload(manifest)
    manifest_path = output_path / "manifest.json"
    _write_json(manifest, manifest_path)
    return {"manifest": manifest, "manifest_path": str(manifest_path), "output_dir": str(output_path)}


def load_corpus_records(path: str | Path) -> List[Dict]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
    return rows


def dependency_status() -> Dict:
    packages = {}
    torch_module = None
    for package_name in ("torch", "transformers", "accelerate", "sentencepiece"):
        try:
            module = __import__(package_name)
            if package_name == "torch":
                torch_module = module
            packages[package_name] = {
                "installed": True,
                "version": getattr(module, "__version__", "unknown"),
            }
        except ImportError:
            packages[package_name] = {
                "installed": False,
                "version": None,
            }
    required = ("torch", "transformers", "accelerate")
    return {
        "ready": all(packages[name]["installed"] for name in required),
        "packages": packages,
        "hardware": _torch_hardware_status(torch_module),
        "install_command": ".\\.venv\\Scripts\\python.exe -m pip install -r backend\\requirements-train.txt",
        "cuda_install_command": (
            ".\\.venv\\Scripts\\python.exe -m pip install --upgrade --force-reinstall torch "
            "--index-url https://download.pytorch.org/whl/cu126"
        ),
    }


def _torch_hardware_status(torch_module) -> Dict:
    status = {
        "cuda_available": False,
        "torch_cuda_version": None,
        "device_count": 0,
        "devices": [],
        "low_vram_recommended": False,
    }
    if torch_module is None:
        return status
    try:
        status["torch_cuda_version"] = getattr(getattr(torch_module, "version", None), "cuda", None)
        cuda = getattr(torch_module, "cuda", None)
        if cuda is None:
            return status
        status["cuda_available"] = bool(cuda.is_available())
        status["device_count"] = int(cuda.device_count())
        for index in range(status["device_count"]):
            props = cuda.get_device_properties(index)
            total_mib = round(props.total_memory / 1024 / 1024, 1)
            free_mib = None
            if status["cuda_available"]:
                try:
                    free_bytes, _total_bytes = cuda.mem_get_info(index)
                    free_mib = round(free_bytes / 1024 / 1024, 1)
                except Exception:
                    free_mib = None
            status["devices"].append(
                {
                    "index": index,
                    "name": cuda.get_device_name(index),
                    "total_memory_mib": total_mib,
                    "free_memory_mib": free_mib,
                    "compute_capability": f"{props.major}.{props.minor}",
                }
            )
        status["low_vram_recommended"] = any(
            device.get("total_memory_mib", 0) and device["total_memory_mib"] <= 6144
            for device in status["devices"]
        )
    except Exception as exc:
        status["error"] = str(exc)
    return status


def train_transformer_model(
    *,
    corpus_dir: str | Path = DEFAULT_TRANSFORMER_CORPUS_DIR,
    output_dir: str | Path = DEFAULT_TRANSFORMER_MODEL_DIR,
    base_model: str = DEFAULT_BASE_MODEL,
    epochs: float = 3.0,
    batch_size: int = 2,
    learning_rate: float = 2e-5,
    save_checkpoints: bool = False,
    gradient_accumulation_steps: int = 1,
    fp16: bool = False,
    gradient_checkpointing: bool = False,
    use_cpu: bool = False,
    optim: str | None = None,
    predict_with_generate: bool = False,
    max_source_length: int = DEFAULT_MAX_SOURCE_LENGTH,
    max_target_length: int = DEFAULT_MAX_TARGET_LENGTH,
) -> Dict:
    deps = dependency_status()
    if not deps["ready"]:
        missing = [name for name, meta in deps["packages"].items() if not meta["installed"]]
        raise RuntimeError(
            "Transformer training dependencies are missing: "
            + ", ".join(missing)
            + f". Install with: {deps['install_command']}"
        )

    # Optional heavy imports stay inside the trainer so normal backend use has no torch dependency.
    import torch
    from torch.utils.data import Dataset
    from transformers import (
        AutoModelForSeq2SeqLM,
        AutoTokenizer,
        DataCollatorForSeq2Seq,
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
    )

    corpus_path = Path(corpus_dir)
    manifest_path = corpus_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Corpus manifest not found: {manifest_path}. Run the prepare command first.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    train_rows = load_corpus_records(corpus_path / "train.jsonl")
    eval_rows = load_corpus_records(corpus_path / "eval.jsonl")

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForSeq2SeqLM.from_pretrained(base_model)
    if gradient_checkpointing and hasattr(model.config, "use_cache"):
        model.config.use_cache = False

    class IntentDataset(Dataset):
        def __init__(self, rows: List[Dict]):
            self.rows = rows

        def __len__(self):
            return len(self.rows)

        def __getitem__(self, index):
            row = self.rows[index]
            model_inputs = tokenizer(
                row["input"],
                max_length=max_source_length,
                truncation=True,
            )
            labels = tokenizer(
                text_target=row["target_json"],
                max_length=max_target_length,
                truncation=True,
            )
            model_inputs["labels"] = labels["input_ids"]
            return model_inputs

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    training_kwargs = {
        "output_dir": str(output_path),
        "num_train_epochs": epochs,
        "per_device_train_batch_size": batch_size,
        "per_device_eval_batch_size": batch_size,
        "learning_rate": learning_rate,
        "predict_with_generate": bool(predict_with_generate),
        "eval_strategy": "epoch",
        "save_strategy": "epoch" if save_checkpoints else "no",
        "logging_strategy": "steps",
        "logging_steps": 10,
        "save_total_limit": 1,
        "report_to": [],
    }
    argument_params = inspect.signature(Seq2SeqTrainingArguments.__init__).parameters
    optional_training_kwargs = {
        "gradient_accumulation_steps": max(1, int(gradient_accumulation_steps)),
        "fp16": bool(fp16),
        "use_cpu": bool(use_cpu),
        "gradient_checkpointing": bool(gradient_checkpointing),
    }
    for key, value in optional_training_kwargs.items():
        if key in argument_params:
            training_kwargs[key] = value
    if optim and "optim" in argument_params:
        training_kwargs["optim"] = optim
    training_args = Seq2SeqTrainingArguments(**training_kwargs)
    trainer_kwargs = {
        "model": model,
        "args": training_args,
        "train_dataset": IntentDataset(train_rows),
        "eval_dataset": IntentDataset(eval_rows),
        "data_collator": DataCollatorForSeq2Seq(tokenizer, model=model),
    }
    trainer_params = inspect.signature(Seq2SeqTrainer.__init__).parameters
    if "processing_class" in trainer_params:
        trainer_kwargs["processing_class"] = tokenizer
    else:
        trainer_kwargs["tokenizer"] = tokenizer
    trainer = Seq2SeqTrainer(**trainer_kwargs)
    train_output = trainer.train()
    trainer.save_model(str(output_path))
    tokenizer.save_pretrained(str(output_path))

    model_contract = {
        "schema": TRANSFORMER_MODEL_CONTRACT_SCHEMA,
        "model_id": "transformer-intent-seq2seq",
        "model_type": "seq2seq_transformer",
        "base_model": base_model,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corpus_digest": manifest.get("corpus_digest"),
        "dataset": {
            "path": manifest.get("dataset", {}).get("path"),
            "augmentation_path": manifest.get("dataset", {}).get("augmentation_path"),
            "adversarial_path": manifest.get("dataset", {}).get("adversarial_path"),
            "train_ids": manifest.get("splits", {}).get("train", {}).get("source_ids", []),
            "augmentation_ids": manifest.get("splits", {}).get("augmentation", {}).get("source_ids", []),
            "eval_ids": manifest.get("splits", {}).get("eval", {}).get("source_ids", []),
            "holdout_ids": manifest.get("splits", {}).get("holdout", {}).get("source_ids", []),
            "adversarial_ids": manifest.get("splits", {}).get("adversarial", {}).get("source_ids", []),
        },
        "contract": manifest["contract"],
        "bounded_output_fields": sorted(BOUNDED_OUTPUT_FIELDS),
        "training": {
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "save_checkpoints": save_checkpoints,
            "gradient_accumulation_steps": max(1, int(gradient_accumulation_steps)),
            "fp16": bool(fp16),
            "gradient_checkpointing": bool(gradient_checkpointing),
            "use_cpu": bool(use_cpu),
            "optim": optim,
            "predict_with_generate": bool(predict_with_generate),
            "max_source_length": max_source_length,
            "max_target_length": max_target_length,
            "train_rows": len(train_rows),
            "eval_rows": len(eval_rows),
            "augmentation_rows": len(manifest.get("splits", {}).get("augmentation", {}).get("source_ids", [])),
            "train_loss": getattr(train_output, "training_loss", None),
        },
        "hardware": deps.get("hardware", {}),
    }
    model_contract["model_digest"] = _digest_payload(model_contract)
    contract_path = output_path / "shepherd_model_contract.json"
    _write_json(model_contract, contract_path)
    return {
        "model_dir": str(output_path),
        "contract_path": str(contract_path),
        "contract": model_contract,
    }


class TransformerIntentAdapter:
    def __init__(self, model_dir: str | Path = DEFAULT_TRANSFORMER_MODEL_DIR):
        deps = dependency_status()
        if not deps["ready"]:
            missing = [name for name, meta in deps["packages"].items() if not meta["installed"]]
            raise RuntimeError(
                "Transformer inference dependencies are missing: "
                + ", ".join(missing)
                + f". Install with: {deps['install_command']}"
            )
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self.model_dir = Path(model_dir)
        self.contract = self._load_contract()
        self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir))
        self.model = AutoModelForSeq2SeqLM.from_pretrained(str(self.model_dir))
        self.model.eval()

    def generate_raw(self, command: str, *, max_new_tokens: int = DEFAULT_MAX_TARGET_LENGTH) -> str:
        import torch

        inputs = self.tokenizer(
            _format_model_input(command),
            return_tensors="pt",
            truncation=True,
            max_length=DEFAULT_MAX_SOURCE_LENGTH,
        )
        model_device = next(self.model.parameters()).device
        inputs = {key: value.to(model_device) for key, value in inputs.items()}
        with torch.no_grad():
            generated = self.model.generate(**inputs, max_new_tokens=max_new_tokens)
        return self.tokenizer.decode(generated[0], skip_special_tokens=True)

    def predict(self, command: str) -> Dict:
        decoded = self.generate_raw(command)
        return coerce_generated_text(
            decoded,
            model_id=self.contract.get("model_id"),
            model_digest=self.contract.get("model_digest"),
        )

    def _load_contract(self) -> Dict:
        contract_path = self.model_dir / "shepherd_model_contract.json"
        if not contract_path.exists():
            raise FileNotFoundError(f"Transformer model contract missing: {contract_path}")
        return json.loads(contract_path.read_text(encoding="utf-8"))


def diagnose_transformer_model(
    model_dir: str | Path = DEFAULT_TRANSFORMER_MODEL_DIR,
    *,
    corpus_dir: str | Path = DEFAULT_TRANSFORMER_CORPUS_DIR,
    split: str = "eval",
    limit: int | None = 20,
    output_path: str | Path | None = None,
    max_new_tokens: int = DEFAULT_MAX_TARGET_LENGTH,
) -> Dict:
    corpus_path = Path(corpus_dir)
    records_path = corpus_path / f"{split}.jsonl"
    if not records_path.exists():
        raise FileNotFoundError(f"Diagnostic split not found: {records_path}")
    rows = load_corpus_records(records_path)
    if limit is not None and limit > 0:
        rows = rows[:limit]

    adapter = TransformerIntentAdapter(model_dir)
    records = []
    for row in rows:
        command = row.get("raw_command") or _strip_task_prefix(row.get("input", ""))
        raw_generated = adapter.generate_raw(command, max_new_tokens=max_new_tokens)
        records.append(
            build_generation_diagnostic_record(
                row,
                raw_generated,
                model_id=adapter.contract.get("model_id"),
                model_digest=adapter.contract.get("model_digest"),
            )
        )

    report = {
        "schema": TRANSFORMER_DIAGNOSTIC_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_dir": str(Path(model_dir)),
        "corpus_dir": str(corpus_path),
        "split": split,
        "limit": limit,
        "max_new_tokens": max_new_tokens,
        "model_id": adapter.contract.get("model_id"),
        "model_digest": adapter.contract.get("model_digest"),
        "summary": summarize_generation_diagnostics(records),
        "records": records,
    }
    if output_path:
        _write_json(report, output_path)
        report["report_path"] = str(Path(output_path))
    return report


def build_generation_diagnostic_record(row: Dict, raw_generated: str, *, model_id: str | None, model_digest: str | None) -> Dict:
    target = json.loads(row.get("target_json") or "{}")
    expected = target.get("intent", {})
    bounded = coerce_generated_text(raw_generated, model_id=model_id, model_digest=model_digest)
    raw_json_valid, raw_intent_object = _raw_generation_shape(raw_generated)
    field_results = {}
    for field in EVALUATED_INTENT_FIELDS:
        if field not in expected:
            continue
        expected_value = expected.get(field)
        predicted_value = bounded.get(field)
        field_results[field] = {
            "expected": expected_value,
            "predicted": predicted_value,
            "matched": _normalize_diagnostic_value(expected_value) == _normalize_diagnostic_value(predicted_value),
        }
    subset_match = all(result["matched"] for result in field_results.values())
    bounded_output = set(bounded).issubset(BOUNDED_OUTPUT_FIELDS) and bounded.get("needs_confirmation") is True
    return {
        "id": row.get("id"),
        "language": row.get("language"),
        "split": row.get("split"),
        "command": row.get("raw_command") or _strip_task_prefix(row.get("input", "")),
        "raw_generated": raw_generated,
        "raw_json_valid": raw_json_valid,
        "raw_intent_object": raw_intent_object,
        "expected_intent": expected,
        "bounded_output": bounded,
        "bounded_output_valid": bounded_output,
        "subset_match": subset_match,
        "field_results": field_results,
    }


def summarize_generation_diagnostics(records: Iterable[Dict]) -> Dict:
    rows = list(records)
    field_totals = {field: 0 for field in EVALUATED_INTENT_FIELDS}
    field_matches = {field: 0 for field in EVALUATED_INTENT_FIELDS}
    raw_generation_counts = {}
    for record in rows:
        raw_text = record.get("raw_generated", "")
        raw_generation_counts[raw_text] = raw_generation_counts.get(raw_text, 0) + 1
        for field, result in record.get("field_results", {}).items():
            field_totals[field] += 1
            if result.get("matched"):
                field_matches[field] += 1
    field_metrics = {
        field: {
            "matched": field_matches[field],
            "total": field_totals[field],
            "accuracy": round(field_matches[field] / field_totals[field], 3) if field_totals[field] else None,
        }
        for field in EVALUATED_INTENT_FIELDS
    }
    top_raw_generations = [
        {"raw_generated": raw_text, "count": count}
        for raw_text, count in sorted(raw_generation_counts.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]
    return {
        "total": len(rows),
        "raw_json_valid_count": sum(1 for record in rows if record.get("raw_json_valid")),
        "raw_intent_object_count": sum(1 for record in rows if record.get("raw_intent_object")),
        "bounded_output_valid_count": sum(1 for record in rows if record.get("bounded_output_valid")),
        "subset_matches": sum(1 for record in rows if record.get("subset_match")),
        "field_metrics": field_metrics,
        "top_raw_generations": top_raw_generations,
    }


def coerce_generated_text(generated_text: str, *, model_id: str | None, model_digest: str | None) -> Dict:
    try:
        parsed = json.loads(generated_text)
    except json.JSONDecodeError:
        parsed = {}
    if "intent" in parsed and isinstance(parsed["intent"], dict):
        parsed = parsed["intent"]
    if not isinstance(parsed, dict):
        parsed = {}
    return coerce_bounded_intent(
        parsed,
        confidence=0.72 if parsed else 0.0,
        model_id=model_id,
        model_digest=model_digest,
        parser_name="transformer_seq2seq",
    )


def _training_record(example: Dict, split_name: str) -> Dict:
    target = {
        "intent": example["expected_intent"],
        "constraints": example["expected_constraints"],
        "should_clarify": bool(example["should_clarify"]),
    }
    return {
        "id": example["id"],
        "language": example["language"],
        "split": split_name,
        "input": _format_model_input(example["command"]),
        "raw_command": example["command"],
        "target_json": json.dumps(target, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        "target_digest": sha256(
            json.dumps(target, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }


def _language_counts(records: Iterable[Dict]) -> Dict[str, int]:
    counts = {}
    for record in records:
        language = record.get("language", "unknown")
        counts[language] = counts.get(language, 0) + 1
    return counts


def _format_model_input(command: str) -> str:
    return f"{TASK_PREFIX}{command}"


def _strip_task_prefix(text: str) -> str:
    return text[len(TASK_PREFIX):] if text.startswith(TASK_PREFIX) else text


def _raw_generation_shape(raw_generated: str) -> tuple[bool, bool]:
    try:
        parsed = json.loads(raw_generated)
    except json.JSONDecodeError:
        return False, False
    if not isinstance(parsed, dict):
        return True, False
    if "intent" in parsed:
        return True, isinstance(parsed["intent"], dict)
    return True, True


def _normalize_diagnostic_value(value):
    if isinstance(value, str):
        return value.strip().lower()
    return value


def _write_jsonl(records: Iterable[Dict], path: str | Path) -> str:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            json.dump(record, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
    return str(output_path)


def _write_json(payload: Dict, path: str | Path) -> str:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return str(output_path)


def _digest_payload(payload: Dict) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Prepare and train Shepherd-AI transformer parser experiments.")
    subparsers = parser.add_subparsers(dest="command")

    prepare_parser = subparsers.add_parser("prepare", help="Write frozen transformer training/evaluation corpora.")
    prepare_parser.add_argument("--dataset", default=str(DEFAULT_BENCHMARK_PATH), help="Benchmark JSONL dataset path.")
    prepare_parser.add_argument("--augmentation", default=None, help="Optional train-only augmentation JSONL path.")
    prepare_parser.add_argument("--adversarial", default=str(DEFAULT_ADVERSARIAL_PATH), help="Adversarial holdout JSONL path.")
    prepare_parser.add_argument("--output-dir", default=str(DEFAULT_TRANSFORMER_CORPUS_DIR), help="Corpus output directory.")

    status_parser = subparsers.add_parser("status", help="Show optional transformer dependency status.")
    status_parser.set_defaults(_status=True)

    train_parser = subparsers.add_parser("train", help="Train the optional transformer parser.")
    train_parser.add_argument("--corpus-dir", default=str(DEFAULT_TRANSFORMER_CORPUS_DIR), help="Prepared corpus directory.")
    train_parser.add_argument("--output-dir", default=str(DEFAULT_TRANSFORMER_MODEL_DIR), help="Model output directory.")
    train_parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL, help="Hugging Face seq2seq base model.")
    train_parser.add_argument("--epochs", type=float, default=3.0, help="Training epochs.")
    train_parser.add_argument("--batch-size", type=int, default=2, help="Per-device batch size.")
    train_parser.add_argument("--learning-rate", type=float, default=2e-5, help="Learning rate.")
    train_parser.add_argument("--max-source-length", type=int, default=DEFAULT_MAX_SOURCE_LENGTH, help="Tokenizer source length.")
    train_parser.add_argument("--max-target-length", type=int, default=DEFAULT_MAX_TARGET_LENGTH, help="Tokenizer target length.")
    train_parser.add_argument(
        "--gradient-accumulation-steps",
        type=int,
        default=1,
        help="Accumulate gradients across steps to simulate a larger batch on low-VRAM GPUs.",
    )
    train_parser.add_argument("--fp16", action="store_true", help="Use CUDA half-precision training.")
    train_parser.add_argument(
        "--gradient-checkpointing",
        action="store_true",
        help="Reduce activation memory at the cost of extra compute.",
    )
    train_parser.add_argument("--use-cpu", action="store_true", help="Force CPU training even when CUDA is available.")
    train_parser.add_argument("--optim", default=None, help="Optional Hugging Face optimizer name, such as adafactor.")
    train_parser.add_argument(
        "--predict-with-generate",
        action="store_true",
        help="Generate during eval. Disabled by default because promotion runs generation separately.",
    )
    train_parser.add_argument(
        "--save-checkpoints",
        action="store_true",
        help="Save epoch checkpoints. Disabled by default to avoid duplicate multi-GB local artifacts.",
    )

    predict_parser = subparsers.add_parser("predict", help="Predict bounded intent from a trained transformer model.")
    predict_parser.add_argument("command_text", help="Operator command to parse.")
    predict_parser.add_argument("--model-dir", default=str(DEFAULT_TRANSFORMER_MODEL_DIR), help="Trained model directory.")
    predict_parser.add_argument("--show-raw", action="store_true", help="Include raw generated model text for diagnostics.")

    diagnose_parser = subparsers.add_parser("diagnose", help="Capture raw transformer generations and field mismatches.")
    diagnose_parser.add_argument("--model-dir", default=str(DEFAULT_TRANSFORMER_MODEL_DIR), help="Trained model directory.")
    diagnose_parser.add_argument("--corpus-dir", default=str(DEFAULT_TRANSFORMER_CORPUS_DIR), help="Prepared corpus directory.")
    diagnose_parser.add_argument("--split", default="eval", choices=["train", "augmentation", "eval", "holdout", "adversarial"], help="Corpus split to diagnose.")
    diagnose_parser.add_argument("--limit", type=int, default=20, help="Maximum rows to diagnose. Use 0 for all rows.")
    diagnose_parser.add_argument("--output", default=None, help="Optional JSON report output path.")
    diagnose_parser.add_argument("--max-new-tokens", type=int, default=DEFAULT_MAX_TARGET_LENGTH, help="Generation token limit.")

    args = parser.parse_args()
    command = args.command or "prepare"

    if command == "prepare":
        result = write_training_corpus(
            args.output_dir,
            dataset_path=args.dataset,
            augmentation_path=args.augmentation,
            adversarial_path=args.adversarial,
        )
        print(json.dumps(_manifest_summary(result), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if command == "status":
        print(json.dumps(dependency_status(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if command == "train":
        result = train_transformer_model(
            corpus_dir=args.corpus_dir,
            output_dir=args.output_dir,
            base_model=args.base_model,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            save_checkpoints=args.save_checkpoints,
            gradient_accumulation_steps=args.gradient_accumulation_steps,
            fp16=args.fp16,
            gradient_checkpointing=args.gradient_checkpointing,
            use_cpu=args.use_cpu,
            optim=args.optim,
            predict_with_generate=args.predict_with_generate,
            max_source_length=args.max_source_length,
            max_target_length=args.max_target_length,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if command == "predict":
        adapter = TransformerIntentAdapter(args.model_dir)
        if args.show_raw:
            raw_generated = adapter.generate_raw(args.command_text)
            prediction = {
                "raw_generated": raw_generated,
                "bounded_output": coerce_generated_text(
                    raw_generated,
                    model_id=adapter.contract.get("model_id"),
                    model_digest=adapter.contract.get("model_digest"),
                ),
            }
        else:
            prediction = adapter.predict(args.command_text)
        print(json.dumps(prediction, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if command == "diagnose":
        report = diagnose_transformer_model(
            args.model_dir,
            corpus_dir=args.corpus_dir,
            split=args.split,
            limit=None if args.limit == 0 else args.limit,
            output_path=args.output,
            max_new_tokens=args.max_new_tokens,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    parser.print_help()
    return 1


def _manifest_summary(result: Dict) -> Dict:
    clone = json.loads(json.dumps(result))
    for split_summary in clone.get("manifest", {}).get("splits", {}).values():
        ids = split_summary.get("source_ids", [])
        split_summary["source_ids"] = f"{len(ids)} ids omitted"
    return clone


if __name__ == "__main__":
    raise SystemExit(main())
