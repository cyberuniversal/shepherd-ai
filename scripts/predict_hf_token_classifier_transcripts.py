"""Run a saved Hugging Face token classifier on transcript JSONL records."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.hf_token_analysis import entities_from_bio  # noqa: E402
from shepherd_ai.span_annotations import spans_to_bio_tags  # noqa: E402
from shepherd_ai.span_intent import (  # noqa: E402
    assemble_hybrid_intent_from_entities,
    assemble_intent_from_entities,
    validate_assembled_intent,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", required=True, help="Input JSONL containing transcript records.")
    parser.add_argument("--model-dir", required=True, help="Saved Hugging Face token-classifier directory.")
    parser.add_argument("--output", required=True, help="Path to write transcript prediction JSON.")
    parser.add_argument("--transcript-field", default="predicted_transcript", help="Field containing transcript text.")
    parser.add_argument("--id-field", default="id", help="Field containing stable record id.")
    parser.add_argument("--split-field", default="split", help="Optional field containing split name.")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--required-device-substring", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        import accelerate
        import torch
        import transformers
        from transformers import AutoModelForTokenClassification, AutoTokenizer
    except ImportError as exc:
        raise SystemExit(
            "Missing Hugging Face inference dependencies. In Colab run: "
            "%pip install -q transformers[torch] accelerate datasets"
        ) from exc

    device, runtime_metadata = _select_runtime(
        torch,
        transformers,
        accelerate,
        required_device_substring=args.required_device_substring,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    if not tokenizer.is_fast:
        raise ValueError("token classification inference requires a fast tokenizer with word_ids() support")
    model = AutoModelForTokenClassification.from_pretrained(args.model_dir)
    model.to(device)
    model.eval()
    id2label = {int(index): str(label) for index, label in model.config.id2label.items()}

    input_records = _read_jsonl(args.input_jsonl)
    output_records = [
        _predict_transcript_record(
            record,
            model=model,
            tokenizer=tokenizer,
            id2label=id2label,
            torch_module=torch,
            device=device,
            id_field=args.id_field,
            split_field=args.split_field,
            transcript_field=args.transcript_field,
        )
        for record in input_records
    ]
    output = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "input_jsonl": args.input_jsonl,
            "model_dir": args.model_dir,
            "transcript_field": args.transcript_field,
            "id_field": args.id_field,
            "split_field": args.split_field,
            "batch_size": args.batch_size,
            "required_device_substring": args.required_device_substring,
            "runtime": runtime_metadata,
            "evaluation_note": (
                "Model-generated span and intent predictions for transcript text. This is not accuracy "
                "unless compared against human-verified gold labels in a separate evaluation."
            ),
        },
        "summary": _summarize(output_records),
        "records": output_records,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(output["summary"], indent=2, sort_keys=True))


def _predict_transcript_record(
    record: dict[str, Any],
    *,
    model: Any,
    tokenizer: Any,
    id2label: dict[int, str],
    torch_module: Any,
    device: Any,
    id_field: str,
    split_field: str,
    transcript_field: str,
) -> dict[str, Any]:
    text = str(record.get(transcript_field, ""))
    token_records = spans_to_bio_tags(text, [])
    tokens = [token.text for token, _ in token_records]
    offsets = [[token.start, token.end] for token, _ in token_records]
    predicted_tags = _predict_tags(tokens, model, tokenizer, id2label, torch_module, device)
    predicted_entities = [list(entity) for entity in entities_from_bio(predicted_tags, offsets)]
    raw_intent = assemble_intent_from_entities(text, predicted_entities)
    hybrid_intent = assemble_hybrid_intent_from_entities(text, predicted_entities)
    return {
        "id": str(record.get(id_field)),
        "split": record.get(split_field, "not stated"),
        "transcript_field": transcript_field,
        "transcript": text,
        "tokens": tokens,
        "offsets": offsets,
        "predicted_tags": predicted_tags,
        "predicted_entities": predicted_entities,
        "span_intent_assembly": raw_intent,
        "span_intent_validation": validate_assembled_intent(raw_intent),
        "hybrid_span_parser": hybrid_intent,
        "hybrid_span_validation": validate_assembled_intent(hybrid_intent),
    }


def _predict_tags(
    tokens: list[str],
    model: Any,
    tokenizer: Any,
    id2label: dict[int, str],
    torch_module: Any,
    device: Any,
) -> list[str]:
    if not tokens:
        return []
    tokenized = tokenizer(tokens, truncation=True, is_split_into_words=True, return_tensors="pt")
    word_ids = tokenized.word_ids(batch_index=0)
    model_inputs = {key: value.to(device) for key, value in tokenized.items()}
    with torch_module.no_grad():
        predictions = model(**model_inputs).logits.argmax(dim=-1)[0].detach().cpu().tolist()
    predicted_by_word: dict[int, str] = {}
    for token_index, word_id in enumerate(word_ids):
        if word_id is None or word_id in predicted_by_word:
            continue
        predicted_by_word[int(word_id)] = id2label[int(predictions[token_index])]
    return [predicted_by_word.get(index, "O") for index in range(len(tokens))]


def _summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(records),
        "predicted_entities": sum(len(record["predicted_entities"]) for record in records),
        "raw_intents_with_validation_issues": sum(
            1 for record in records if record["span_intent_validation"].get("issues")
        ),
        "hybrid_intents_with_validation_issues": sum(
            1 for record in records if record["hybrid_span_validation"].get("issues")
        ),
    }


def _select_runtime(
    torch_module: Any,
    transformers_module: Any,
    accelerate_module: Any,
    *,
    required_device_substring: str,
) -> tuple[Any, dict[str, Any]]:
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
        "datasets_version": _package_version("datasets"),
    }


def _package_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "not installed"


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    main()
