# LLM Setup

Shepherd-AI can parse commands in two modes:

- `llm`: Ollama is running and the configured model responds.
- `heuristic_fallback`: Ollama is unavailable, the model is missing, or generation fails, so deterministic local parsing is used.

The dashboard shows parser mode in Tactical Logs, the Plan Preview panel, and the `Program` tab under `Prompt-To-Drone Proof`.

## Install Ollama

Install Ollama from:

```text
https://ollama.com/download
```

Then pull the recommended demo model used by Shepherd-AI:

```bash
ollama pull llama3.1:8b
```

If the laptop struggles with the 8B model, use the smaller model and set `SHEPHERD_LLM_MODEL` before starting the backend:

```bash
ollama pull gemma2:2b
export SHEPHERD_LLM_MODEL=gemma2:2b
```

Start Ollama if it is not already running:

```bash
ollama serve
```

Shepherd-AI checks Ollama at:

```text
http://localhost:11434
```

## Verify

With Shepherd-AI running, open:

```text
http://localhost:8000/api/parser/status
```

If Ollama was available when the first command was parsed, command responses should show `parser: llm`. If not, they show `heuristic` and continue working offline.

The status response includes:

- `llm_online`: Ollama is running and the configured model is installed.
- `model_missing`: Ollama is running, but the model must be pulled.
- `ollama_running`: Ollama server reachability.
- `fallback_active`: deterministic fallback is currently being used.

## Plan-First Flow

Normal dashboard commands call `POST /api/mission/plan`. The LLM only proposes intent JSON, for example:

```json
{
  "action": "rendezvous",
  "target_zone": "al nada",
  "target_reference": null,
  "drone_count": 2,
  "needs_confirmation": true,
  "confidence": 0.86,
  "clarifying_question": "Do you mean Al Nada district in Riyadh?"
}
```

The backend then resolves the target, assigns drones on a cloned digital twin, runs safety, compiles `SHEPHERD-IR`, and returns a plan preview. Nothing moves until `POST /api/mission/confirm` is called.

## Safety Boundary

The LLM never controls MAVSDK or PX4 directly. Its output is treated as intent JSON, then Shepherd-AI applies deterministic target resolution, fleet allocation, safety checks, confirmation, and `SHEPHERD-IR` compilation before anything is dispatched.
