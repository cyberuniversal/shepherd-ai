"""Evaluate a saved Hugging Face token classifier with record-level errors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.hf_token_analysis import (  # noqa: E402
    evaluate_hf_token_predictions,
    summarize_hf_token_evaluation,
)
from shepherd_ai.span_training import analyze_span_tagger_errors  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", required=True, help="Directory from export_hf_token_dataset.py.")
    parser.add_argument("--model-dir", required=True, help="Saved Hugging Face model directory.")
    parser.add_argument("--split", default="test", choices=["train", "validation", "test"])
    parser.add_argument("--evaluation-output", required=True, help="Path to write record-level evaluation JSON.")
    parser.add_argument("--error-analysis-output", help="Optional path to write BIO error analysis JSON.")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--required-device-substring", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        import accelerate
        import datasets as datasets_package
        import torch
        import transformers
        from transformers import AutoModelForTokenClassification, AutoTokenizer
    except ImportError as exc:
        raise SystemExit(
            "Missing Hugging Face evaluation dependencies. In Colab run: "
            "%pip install -q transformers[torch] accelerate datasets seqeval"
        ) from exc

    device, runtime_metadata = _select_runtime(
        torch,
        transformers,
        accelerate,
        datasets_package,
        required_device_substring=args.required_device_substring,
    )
    dataset_dir = Path(args.dataset_dir)
    records = _read_jsonl(dataset_dir / f"{args.split}.jsonl")
    label_map = json.loads((dataset_dir / "label_map.json").read_text(encoding="utf-8"))
    id2label = {int(index): str(label) for index, label in label_map["id2label"].items()}
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    if not tokenizer.is_fast:
        raise ValueError("token classification evaluation requires a fast tokenizer with word_ids() support")
    model = AutoModelForTokenClassification.from_pretrained(args.model_dir)
    model.to(device)
    model.eval()

    predictions_by_id = {
        str(record["id"]): _predict_record_tags(record, model, tokenizer, id2label, torch, device)
        for record in records
    }
    evaluation = evaluate_hf_token_predictions(
        records,
        predictions_by_id,
        dataset_name=f"{dataset_dir}/{args.split}.jsonl",
        model_name="hf_token_classifier",
        metadata={
            "model_dir": args.model_dir,
            "split": args.split,
            "batch_size": args.batch_size,
            "required_device_substring": args.required_device_substring,
            "runtime": runtime_metadata,
        },
    )
    output = Path(args.evaluation_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evaluation, indent=2, sort_keys=True), encoding="utf-8")
    if args.error_analysis_output:
        analysis = analyze_span_tagger_errors(evaluation)
        analysis_output = Path(args.error_analysis_output)
        analysis_output.parent.mkdir(parents=True, exist_ok=True)
        analysis_output.write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summarize_hf_token_evaluation(evaluation), indent=2, sort_keys=True))


def _predict_record_tags(record: dict, model, tokenizer, id2label: dict[int, str], torch_module, device) -> list[str]:
    tokenized = tokenizer(record["tokens"], truncation=True, is_split_into_words=True, return_tensors="pt")
    word_ids = tokenized.word_ids(batch_index=0)
    model_inputs = {key: value.to(device) for key, value in tokenized.items()}
    with torch_module.no_grad():
        predictions = model(**model_inputs).logits.argmax(dim=-1)[0].detach().cpu().tolist()
    predicted_by_word: dict[int, str] = {}
    for token_index, word_id in enumerate(word_ids):
        if word_id is None or word_id in predicted_by_word:
            continue
        predicted_by_word[int(word_id)] = id2label[int(predictions[token_index])]
    return [predicted_by_word.get(index, "O") for index in range(len(record["tokens"]))]


def _select_runtime(
    torch_module,
    transformers_module,
    accelerate_module,
    datasets_module,
    *,
    required_device_substring: str,
) -> tuple[object, dict]:
    cuda_available = bool(torch_module.cuda.is_available())
    device_names = [
        torch_module.cuda.get_device_name(index) for index in range(torch_module.cuda.device_count())
    ]
    if required_device_substring:
        required = required_device_substring.lower()
        if not cuda_available or not any(required in name.lower() for name in device_names):
            raise SystemExit(
                "Required CUDA device substring not found. "
                f"Required: {required_device_substring!r}; available devices: {device_names!r}"
            )
    device = torch_module.device("cuda" if cuda_available else "cpu")
    return device, {
        "cuda_available": cuda_available,
        "cuda_device_names": device_names,
        "torch_version": torch_module.__version__,
        "transformers_version": transformers_module.__version__,
        "accelerate_version": accelerate_module.__version__,
        "datasets_version": datasets_module.__version__,
    }


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    main()
