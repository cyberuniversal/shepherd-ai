import argparse
import json
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
    from backend.mission_dataset import DEFAULT_ADVERSARIAL_PATH, DEFAULT_BENCHMARK_PATH
except ImportError:
    from learned_parser import BOUNDED_OUTPUT_FIELDS, coerce_bounded_intent, load_frozen_splits
    from mission_dataset import DEFAULT_ADVERSARIAL_PATH, DEFAULT_BENCHMARK_PATH


TRANSFORMER_CORPUS_SCHEMA = "shepherd-transformer-parser-corpus/1.0"
TRANSFORMER_MODEL_CONTRACT_SCHEMA = "shepherd-transformer-parser-contract/1.0"
DEFAULT_TRANSFORMER_CORPUS_DIR = Path(".tmp_models/transformer_parser/corpus")
DEFAULT_TRANSFORMER_MODEL_DIR = Path(".tmp_models/transformer_parser/model")
DEFAULT_BASE_MODEL = "google/mt5-small"
DEFAULT_MAX_SOURCE_LENGTH = 160
DEFAULT_MAX_TARGET_LENGTH = 320


def write_training_corpus(
    output_dir: str | Path = DEFAULT_TRANSFORMER_CORPUS_DIR,
    *,
    dataset_path: str | Path = DEFAULT_BENCHMARK_PATH,
    adversarial_path: str | Path | None = DEFAULT_ADVERSARIAL_PATH,
) -> Dict:
    splits = load_frozen_splits(dataset_path, adversarial_path=adversarial_path)
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
            "used_for_training": split_name == "train",
            "languages": _language_counts(records),
            "source_ids": [record["id"] for record in records],
        }

    manifest = {
        "schema": TRANSFORMER_CORPUS_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "path": str(Path(dataset_path)),
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
    for package_name in ("torch", "transformers", "accelerate", "sentencepiece"):
        try:
            module = __import__(package_name)
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
        "install_command": ".\\.venv\\Scripts\\python.exe -m pip install -r backend\\requirements-train.txt",
    }


def train_transformer_model(
    *,
    corpus_dir: str | Path = DEFAULT_TRANSFORMER_CORPUS_DIR,
    output_dir: str | Path = DEFAULT_TRANSFORMER_MODEL_DIR,
    base_model: str = DEFAULT_BASE_MODEL,
    epochs: float = 3.0,
    batch_size: int = 2,
    learning_rate: float = 2e-5,
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
    training_args = Seq2SeqTrainingArguments(
        output_dir=str(output_path),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        predict_with_generate=True,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_strategy="steps",
        logging_steps=10,
        save_total_limit=2,
        report_to=[],
    )
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=IntentDataset(train_rows),
        eval_dataset=IntentDataset(eval_rows),
        tokenizer=tokenizer,
        data_collator=DataCollatorForSeq2Seq(tokenizer, model=model),
    )
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
            "adversarial_path": manifest.get("dataset", {}).get("adversarial_path"),
            "train_ids": manifest.get("splits", {}).get("train", {}).get("source_ids", []),
            "eval_ids": manifest.get("splits", {}).get("eval", {}).get("source_ids", []),
            "holdout_ids": manifest.get("splits", {}).get("holdout", {}).get("source_ids", []),
            "adversarial_ids": manifest.get("splits", {}).get("adversarial", {}).get("source_ids", []),
        },
        "train_rows": len(train_rows),
        "eval_rows": len(eval_rows),
        "contract": manifest["contract"],
        "bounded_output_fields": sorted(BOUNDED_OUTPUT_FIELDS),
        "training": {
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "train_loss": getattr(train_output, "training_loss", None),
        },
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

    def predict(self, command: str) -> Dict:
        import torch

        inputs = self.tokenizer(command, return_tensors="pt", truncation=True, max_length=DEFAULT_MAX_SOURCE_LENGTH)
        with torch.no_grad():
            generated = self.model.generate(**inputs, max_new_tokens=DEFAULT_MAX_TARGET_LENGTH)
        decoded = self.tokenizer.decode(generated[0], skip_special_tokens=True)
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
        "input": example["command"],
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

    predict_parser = subparsers.add_parser("predict", help="Predict bounded intent from a trained transformer model.")
    predict_parser.add_argument("command_text", help="Operator command to parse.")
    predict_parser.add_argument("--model-dir", default=str(DEFAULT_TRANSFORMER_MODEL_DIR), help="Trained model directory.")

    args = parser.parse_args()
    command = args.command or "prepare"

    if command == "prepare":
        result = write_training_corpus(
            args.output_dir,
            dataset_path=args.dataset,
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
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if command == "predict":
        adapter = TransformerIntentAdapter(args.model_dir)
        print(json.dumps(adapter.predict(args.command_text), ensure_ascii=False, indent=2, sort_keys=True))
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
