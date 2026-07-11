"""Fine-tune a Hugging Face token classifier on exported Shepherd-AI spans.

This script is intended for Google Colab with a CUDA GPU runtime. The Week 2
transformer baseline should not silently train on CPU.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", required=True, help="Directory from export_hf_token_dataset.py.")
    parser.add_argument("--pretrained-model", required=True, help="Hugging Face model id or local model path.")
    parser.add_argument("--output-dir", required=True, help="Directory for trained HF model/checkpoints.")
    parser.add_argument("--metrics-output", required=True, help="Path to write test metrics JSON.")
    parser.add_argument("--validation-output", help="Optional path to write validation metrics JSON.")
    parser.add_argument("--epochs", type=float, default=5.0)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument(
        "--required-device-substring",
        default="",
        help="Optional case-insensitive CUDA device-name substring, e.g. T4 for Colab T4 runs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        import accelerate
        import datasets as datasets_package
        import numpy as np
        import torch
        import transformers
        from datasets import Dataset, DatasetDict
        from seqeval.metrics import f1_score, precision_score, recall_score
        from transformers import (
            AutoModelForTokenClassification,
            AutoTokenizer,
            DataCollatorForTokenClassification,
            Trainer,
            TrainingArguments,
            set_seed,
        )
    except ImportError as exc:
        raise SystemExit(
            "Missing Hugging Face training dependencies. In Colab run: "
            "%pip install -q transformers[torch] accelerate datasets seqeval"
        ) from exc

    random.seed(args.seed)
    set_seed(args.seed)
    runtime_metadata = _require_cuda_runtime(
        torch,
        transformers,
        accelerate,
        datasets_package,
        required_device_substring=args.required_device_substring,
    )
    dataset_dir = Path(args.dataset_dir)
    label_map = json.loads((dataset_dir / "label_map.json").read_text(encoding="utf-8"))
    labels = list(label_map["labels"])
    label2id = {label: int(index) for label, index in label_map["label2id"].items()}
    id2label = {int(index): label for index, label in label_map["id2label"].items()}

    raw_datasets = DatasetDict(
        {
            split: Dataset.from_list(_read_jsonl(dataset_dir / f"{split}.jsonl"))
            for split in ("train", "validation", "test")
        }
    )
    tokenizer = AutoTokenizer.from_pretrained(args.pretrained_model)
    if not tokenizer.is_fast:
        raise ValueError("token classification training requires a fast tokenizer with word_ids() support")

    def tokenize_and_align_labels(examples):
        tokenized = tokenizer(examples["tokens"], truncation=True, is_split_into_words=True)
        aligned_labels = []
        for batch_index, tags in enumerate(examples["ner_tags"]):
            word_ids = tokenized.word_ids(batch_index=batch_index)
            previous_word_id = None
            label_ids = []
            for word_id in word_ids:
                if word_id is None:
                    label_ids.append(-100)
                elif word_id != previous_word_id:
                    label_ids.append(tags[word_id])
                else:
                    label_ids.append(-100)
                previous_word_id = word_id
            aligned_labels.append(label_ids)
        tokenized["labels"] = aligned_labels
        return tokenized

    tokenized_datasets = raw_datasets.map(tokenize_and_align_labels, batched=True)
    model = AutoModelForTokenClassification.from_pretrained(
        args.pretrained_model,
        num_labels=len(labels),
        id2label=id2label,
        label2id=label2id,
    )
    data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)

    def compute_metrics(eval_prediction):
        logits, label_ids = eval_prediction
        predictions = np.argmax(logits, axis=-1)
        true_predictions = []
        true_labels = []
        for prediction, label_id in zip(predictions, label_ids):
            pred_labels = []
            gold_labels = []
            for predicted_id, gold_id in zip(prediction, label_id):
                if gold_id == -100:
                    continue
                pred_labels.append(labels[int(predicted_id)])
                gold_labels.append(labels[int(gold_id)])
            true_predictions.append(pred_labels)
            true_labels.append(gold_labels)
        return {
            "entity_precision": precision_score(true_labels, true_predictions),
            "entity_recall": recall_score(true_labels, true_predictions),
            "entity_f1": f1_score(true_labels, true_predictions),
        }

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        num_train_epochs=args.epochs,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="entity_f1",
        seed=args.seed,
        report_to=[],
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["validation"],
        processing_class=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )
    trainer.train()
    validation_metrics = trainer.evaluate(tokenized_datasets["validation"])
    test_metrics = trainer.evaluate(tokenized_datasets["test"])
    _write_metrics(args.metrics_output, test_metrics, args, split="test", runtime_metadata=runtime_metadata)
    if args.validation_output:
        _write_metrics(
            args.validation_output,
            validation_metrics,
            args,
            split="validation",
            runtime_metadata=runtime_metadata,
        )
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(json.dumps({"validation": validation_metrics, "test": test_metrics}, indent=2, sort_keys=True))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _require_cuda_runtime(
    torch_module,
    transformers_module,
    accelerate_module,
    datasets_module,
    *,
    required_device_substring: str,
) -> dict:
    if not torch_module.cuda.is_available():
        raise SystemExit(
            "CUDA GPU is required for Hugging Face Week 2 training. "
            "In Google Colab, select Runtime > Change runtime type > T4 GPU, then rerun."
        )
    device_names = [
        torch_module.cuda.get_device_name(index) for index in range(torch_module.cuda.device_count())
    ]
    if required_device_substring:
        required = required_device_substring.lower()
        if not any(required in name.lower() for name in device_names):
            raise SystemExit(
                "Required CUDA device substring not found. "
                f"Required: {required_device_substring!r}; available devices: {device_names!r}"
            )
    return {
        "cuda_available": True,
        "cuda_device_names": device_names,
        "torch_version": torch_module.__version__,
        "transformers_version": transformers_module.__version__,
        "accelerate_version": accelerate_module.__version__,
        "datasets_version": datasets_module.__version__,
    }


def _write_metrics(
    path: str | Path,
    metrics: dict,
    args: argparse.Namespace,
    *,
    split: str,
    runtime_metadata: dict,
) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": {
            "model_name": "hf_token_classifier",
            "pretrained_model": args.pretrained_model,
            "split": split,
            "seed": args.seed,
            "epochs": args.epochs,
            "learning_rate": args.learning_rate,
            "batch_size": args.batch_size,
            "dataset_dir": args.dataset_dir,
            "required_device_substring": args.required_device_substring,
            "runtime": runtime_metadata,
        },
        "metrics": metrics,
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
