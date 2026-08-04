"""Local-only Hugging Face Qwen backend for the MultiUAV method runner."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
from pathlib import Path
from time import perf_counter
from typing import Any

from shepherd_ai.multiuav_model_revisions import REGISTERED_MODEL_REVISIONS
from shepherd_ai.multiuav_offline_runtime import offline_inference_guard
from shepherd_ai.multiuav_prompts import PromptRequest
from shepherd_ai.multiuav_runner import GenerationResult


_REGISTERED_REVISIONS = {
    item.model_id: item.revision for item in REGISTERED_MODEL_REVISIONS
}
_DTYPES = frozenset({"float16", "bfloat16", "float32"})


@dataclass(frozen=True)
class QwenBackendConfig:
    model_id: str
    revision: str
    max_new_tokens: int
    dtype: str
    cache_dir: str | None = None
    snapshot_dir: str | None = None
    offload_folder: str | None = None
    device_map: str = "auto"

    def validate(self) -> None:
        if _REGISTERED_REVISIONS.get(self.model_id) != self.revision:
            raise ValueError(
                "model id/revision is absent from the frozen registry"
            )
        if (
            not isinstance(self.max_new_tokens, int)
            or isinstance(self.max_new_tokens, bool)
            or self.max_new_tokens <= 0
        ):
            raise ValueError("max_new_tokens must be a positive integer")
        if self.dtype not in _DTYPES:
            raise ValueError(f"unsupported dtype: {self.dtype!r}")
        if self.cache_dir is not None and not self.cache_dir.strip():
            raise ValueError("cache_dir must be non-empty when supplied")
        if self.snapshot_dir is not None:
            if not self.snapshot_dir.strip():
                raise ValueError("snapshot_dir must be non-empty when supplied")
            snapshot = Path(self.snapshot_dir).resolve()
            if not snapshot.is_dir():
                raise ValueError("snapshot_dir must be an existing directory")
            if snapshot.name != self.revision:
                raise ValueError("snapshot_dir does not match the pinned revision")
            if self.cache_dir is not None and not snapshot.is_relative_to(
                Path(self.cache_dir).resolve()
            ):
                raise ValueError("snapshot_dir must stay within cache_dir")
        if self.offload_folder is not None:
            if not self.offload_folder.strip():
                raise ValueError("offload_folder must be non-empty when supplied")
            if not Path(self.offload_folder).resolve().is_dir():
                raise ValueError("offload_folder must be an existing directory")
        if not self.device_map.strip():
            raise ValueError("device_map must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "model_id": self.model_id,
            "revision": self.revision,
            "max_new_tokens": self.max_new_tokens,
            "dtype": self.dtype,
            "cache_dir": self.cache_dir,
            "snapshot_dir": self.snapshot_dir,
            "offload_folder": self.offload_folder,
            "device_map": self.device_map,
            "local_files_only": True,
            "trust_remote_code": False,
            "use_safetensors": True,
            "do_sample": False,
            "num_beams": 1,
        }


class LocalQwenBackend:
    """Generate with an already cached immutable Qwen checkpoint."""

    def __init__(
        self,
        *,
        config: QwenBackendConfig,
        tokenizer: Any,
        model: Any,
        transformers_module: Any,
        torch_module: Any,
    ) -> None:
        config.validate()
        self.config = config
        self._tokenizer = tokenizer
        self._model = model
        self._transformers = transformers_module
        self._torch = torch_module

    @classmethod
    def from_cached(
        cls,
        config: QwenBackendConfig,
        *,
        transformers_module: Any | None = None,
        torch_module: Any | None = None,
    ) -> "LocalQwenBackend":
        """Load a pinned checkpoint without permitting a download."""

        config.validate()
        transformers_module = transformers_module or importlib.import_module(
            "transformers"
        )
        torch_module = torch_module or importlib.import_module("torch")
        model_source = config.snapshot_dir or config.model_id
        common_kwargs: dict[str, Any] = {
            "local_files_only": True,
            "trust_remote_code": False,
        }
        if config.snapshot_dir is None:
            common_kwargs["revision"] = config.revision
        if config.cache_dir is not None:
            common_kwargs["cache_dir"] = config.cache_dir
        model_kwargs = {
            **common_kwargs,
            "device_map": config.device_map,
            "dtype": getattr(torch_module, config.dtype),
            "use_safetensors": True,
        }
        if config.offload_folder is not None:
            model_kwargs["offload_folder"] = config.offload_folder
            model_kwargs["offload_state_dict"] = True
        with offline_inference_guard():
            tokenizer = transformers_module.AutoTokenizer.from_pretrained(
                model_source,
                **common_kwargs,
            )
            model = transformers_module.AutoModelForCausalLM.from_pretrained(
                model_source,
                **model_kwargs,
            )
        model.eval()
        return cls(
            config=config,
            tokenizer=tokenizer,
            model=model,
            transformers_module=transformers_module,
            torch_module=torch_module,
        )

    def generate(self, request: PromptRequest) -> GenerationResult:
        """Generate one deterministic raw response under network isolation."""

        if not isinstance(request, PromptRequest):
            raise TypeError("request must be a PromptRequest")
        messages = [message.to_dict() for message in request.messages]
        device = getattr(self._model, "device", None)
        with offline_inference_guard():
            self._synchronize_if_cuda(device)
            started = perf_counter()
            model_inputs = self._tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
                return_dict=True,
            )
            model_inputs = _move_inputs(model_inputs, device)
            input_ids = model_inputs["input_ids"]
            input_tokens = int(input_ids.shape[-1])
            pad_token_id = getattr(self._tokenizer, "pad_token_id", None)
            if pad_token_id is None:
                pad_token_id = getattr(self._tokenizer, "eos_token_id", None)
            generation_kwargs = {
                **dict(model_inputs),
                "max_new_tokens": self.config.max_new_tokens,
                "do_sample": False,
                "num_beams": 1,
            }
            if pad_token_id is not None:
                generation_kwargs["pad_token_id"] = pad_token_id
            with self._torch.inference_mode():
                sequences = self._model.generate(**generation_kwargs)
            self._synchronize_if_cuda(device)
            latency_ms = (perf_counter() - started) * 1000.0
            generated_tokens = sequences[0][input_tokens:]
            output_tokens = len(generated_tokens)
            raw_output = self._tokenizer.decode(
                generated_tokens,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )
        return GenerationResult(
            raw_output=raw_output,
            generation_status="GENERATED",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            metadata={
                "backend_type": type(self).__name__,
                "model_id": self.config.model_id,
                "model_revision": self.config.revision,
                "dtype": self.config.dtype,
                "device": str(device),
                "device_map": self.config.device_map,
                "cache_dir": self.config.cache_dir,
                "snapshot_dir": self.config.snapshot_dir,
                "offload_folder": self.config.offload_folder,
                "local_files_only": True,
                "trust_remote_code": False,
                "use_safetensors": True,
                "do_sample": False,
                "num_beams": 1,
                "max_new_tokens": self.config.max_new_tokens,
                "non_loopback_sockets_blocked": True,
                "offline_environment": [
                    "HF_HUB_OFFLINE",
                    "TRANSFORMERS_OFFLINE",
                ],
                "transformers_version": str(
                    getattr(self._transformers, "__version__", "not stated")
                ),
                "torch_version": str(
                    getattr(self._torch, "__version__", "not stated")
                ),
            },
        )

    def _synchronize_if_cuda(self, device: Any) -> None:
        cuda = getattr(self._torch, "cuda", None)
        if (
            cuda is not None
            and str(device).startswith("cuda")
            and cuda.is_available()
        ):
            cuda.synchronize()


def _move_inputs(model_inputs: Any, device: Any) -> dict[str, Any]:
    if not isinstance(model_inputs, dict):
        try:
            model_inputs = dict(model_inputs)
        except (TypeError, ValueError) as error:
            raise TypeError(
                "tokenizer chat template must return a mapping"
            ) from error
    if device is None:
        return dict(model_inputs)
    return {
        name: value.to(device) if hasattr(value, "to") else value
        for name, value in model_inputs.items()
    }
