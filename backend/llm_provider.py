import os
import time
from typing import Any, Dict

import httpx


class LLMProviderError(RuntimeError):
    pass


class OllamaProvider:
    """Local Ollama JSON provider used only for intent extraction."""

    def __init__(self, base_url: str | None = None, model_name: str | None = None):
        self.base_url = (base_url or os.getenv("SHEPHERD_OLLAMA_URL") or "http://localhost:11434").rstrip("/")
        self.model_name = model_name or os.getenv("SHEPHERD_LLM_MODEL") or "llama3.1:8b"
        self._status: Dict[str, Any] = {
            "provider": "ollama",
            "endpoint": self.base_url,
            "model": self.model_name,
            "ollama_running": False,
            "model_available": False,
            "model_missing": False,
            "llm_online": False,
            "state": "unknown",
            "message": "LLM status has not been checked yet.",
            "last_error": None,
            "checked_at": None,
        }
        self._last_check = 0.0
        self._cache_ttl_s = 5.0

    def status(self) -> Dict[str, Any]:
        return dict(self._status)

    def _model_matches(self, available_name: str) -> bool:
        if available_name == self.model_name:
            return True
        if ":" not in self.model_name and available_name.startswith(f"{self.model_name}:"):
            return True
        return False

    async def refresh_status(self, force: bool = False) -> Dict[str, Any]:
        now = time.time()
        if not force and self._status["checked_at"] and now - self._last_check < self._cache_ttl_s:
            return self.status()

        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.base_url}/api/tags", timeout=2.0)
                res.raise_for_status()
                models = res.json().get("models", [])
        except Exception as exc:
            self._status.update({
                "ollama_running": False,
                "model_available": False,
                "model_missing": False,
                "llm_online": False,
                "state": "ollama_not_running",
                "message": "Ollama is not running or is unreachable.",
                "last_error": str(exc),
                "checked_at": now,
            })
            self._last_check = now
            return self.status()

        model_names = [model.get("name", "") for model in models]
        model_available = any(self._model_matches(name) for name in model_names)
        self._status.update({
            "ollama_running": True,
            "model_available": model_available,
            "model_missing": not model_available,
            "llm_online": model_available,
            "state": "llm_online" if model_available else "model_missing",
            "message": "LLM online." if model_available else f"Ollama is running, but model {self.model_name} is missing.",
            "last_error": None if model_available else f"Pull model with: ollama pull {self.model_name}",
            "checked_at": now,
            "available_models": model_names,
        })
        self._last_check = now
        return self.status()

    async def generate_json(self, prompt: str) -> str:
        status = await self.refresh_status()
        if not status.get("llm_online"):
            raise LLMProviderError(status.get("message") or "LLM unavailable")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json().get("response", "{}")
        except Exception as exc:
            self._status.update({
                "llm_online": False,
                "state": "generation_failed",
                "message": "Ollama generation failed; fallback parser is active.",
                "last_error": str(exc),
                "checked_at": time.time(),
            })
            raise LLMProviderError(str(exc)) from exc
