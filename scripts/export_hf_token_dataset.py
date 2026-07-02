"""Export human-verified span labels for Hugging Face token classification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.span_training import records_from_span_commands, summarize_span_tag_records  # noqa: E402


LABEL_LIST = [
    "O",
    "B-action",
    "I-action",
    "B-count",
    "I-count",
    "B-location",
    "I-location",
    "B-target",
    "I-target",
    "B-constraint",
    "I-constraint",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="Span-labeled command JSONL.")
    parser.add_argument("--output-dir", required=True, help="Directory for HF token-classification files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = records_from_span_commands(args.dataset)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    label2id = {label: index for index, label in enumerate(LABEL_LIST)}
    id2label = {str(index): label for label, index in label2id.items()}
    _validate_labels(records, label2id)

    for split in ("train", "validation", "test"):
        split_records = [record for record in records if record.split == split]
        _write_jsonl(output_dir / f"{split}.jsonl", [_to_hf_record(record, label2id) for record in split_records])

    label_map = {
        "labels": LABEL_LIST,
        "label2id": label2id,
        "id2label": id2label,
    }
    (output_dir / "label_map.json").write_text(json.dumps(label_map, indent=2, sort_keys=True), encoding="utf-8")
    summary = summarize_span_tag_records(records)
    summary["format"] = "huggingface_token_classification_jsonl"
    summary["files"] = {
        "train": "train.jsonl",
        "validation": "validation.jsonl",
        "test": "test.jsonl",
        "label_map": "label_map.json",
    }
    (output_dir / "dataset_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


def _to_hf_record(record, label2id: dict[str, int]) -> dict:
    return {
        "id": record.id,
        "text": record.text,
        "split": record.split,
        "source": record.source,
        "data_type": record.data_type,
        "tokens": record.tokens,
        "offsets": record.offsets,
        "labels": record.tags,
        "ner_tags": [label2id[tag] for tag in record.tags],
    }


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def _validate_labels(records, label2id: dict[str, int]) -> None:
    unknown = sorted({tag for record in records for tag in record.tags if tag not in label2id})
    if unknown:
        raise ValueError(f"dataset contains unsupported BIO labels: {unknown}")


if __name__ == "__main__":
    main()
