"""Lazy Hugging Face token-classifier adapter for Shepherd span inference."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shepherd_ai.hf_token_analysis import entities_from_bio
from shepherd_ai.span_annotations import spans_to_bio_tags


class HfTokenClassifierSpanPredictor:
    """Load and invoke a saved token classifier without parser substitution."""

    def __init__(
        self,
        *,
        model_name: str,
        model: Any,
        tokenizer: Any,
        id2label: dict[int, str],
        torch_module: Any,
        device: Any,
        runtime_metadata: dict[str, Any],
    ) -> None:
        self.model_name = model_name
        self._model = model
        self._tokenizer = tokenizer
        self._id2label = id2label
        self._torch = torch_module
        self._device = device
        self.runtime_metadata = runtime_metadata

    @classmethod
    def from_model_dir(
        cls,
        model_dir: Path,
        *,
        required_device_substring: str = "",
    ) -> "HfTokenClassifierSpanPredictor":
        try:
            import torch
            import transformers
            from transformers import AutoModelForTokenClassification, AutoTokenizer
        except ImportError as error:
            raise RuntimeError(
                "Hugging Face span inference requires torch and transformers"
            ) from error

        resolved = model_dir.resolve()
        if not resolved.is_dir():
            raise ValueError(f"token-classifier directory does not exist: {resolved}")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        device_name = (
            torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
        )
        if (
            required_device_substring
            and required_device_substring.lower() not in device_name.lower()
        ):
            raise RuntimeError(
                f"required device containing {required_device_substring!r}; "
                f"found {device_name!r}"
            )

        tokenizer = AutoTokenizer.from_pretrained(
            resolved,
            local_files_only=True,
            trust_remote_code=False,
        )
        if not tokenizer.is_fast:
            raise ValueError(
                "token classification inference requires a fast tokenizer"
            )
        model = AutoModelForTokenClassification.from_pretrained(
            resolved,
            local_files_only=True,
            trust_remote_code=False,
        )
        model.to(device)
        model.eval()
        id2label = {
            int(index): str(label)
            for index, label in model.config.id2label.items()
        }
        return cls(
            model_name=resolved.name,
            model=model,
            tokenizer=tokenizer,
            id2label=id2label,
            torch_module=torch,
            device=device,
            runtime_metadata={
                "model_dir": str(resolved),
                "device": str(device),
                "device_name": device_name,
                "torch_version": str(torch.__version__),
                "transformers_version": str(transformers.__version__),
                "local_files_only": True,
                "trust_remote_code": False,
            },
        )

    def predict_entities(self, text: str) -> list[list[Any]]:
        token_records = spans_to_bio_tags(text, [])
        tokens = [token.text for token, _ in token_records]
        offsets = [[token.start, token.end] for token, _ in token_records]
        if not tokens:
            return []
        tokenized = self._tokenizer(
            tokens,
            truncation=True,
            is_split_into_words=True,
            return_tensors="pt",
        )
        word_ids = tokenized.word_ids(batch_index=0)
        model_inputs = {
            key: value.to(self._device)
            for key, value in tokenized.items()
        }
        with self._torch.inference_mode():
            predictions = (
                self._model(**model_inputs)
                .logits.argmax(dim=-1)[0]
                .detach()
                .cpu()
                .tolist()
            )
        predicted_by_word: dict[int, str] = {}
        for token_index, word_id in enumerate(word_ids):
            if word_id is None or word_id in predicted_by_word:
                continue
            predicted_by_word[int(word_id)] = self._id2label[
                int(predictions[token_index])
            ]
        tags = [
            predicted_by_word.get(index, "O")
            for index in range(len(tokens))
        ]
        return [
            list(entity)
            for entity in entities_from_bio(tags, offsets)
        ]
