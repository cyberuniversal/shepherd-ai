# LLM Setup

Shepherd-AI can parse commands in two modes:

- `llm`: Ollama is running and the configured model responds.
- `heuristic_fallback`: Ollama is unavailable, so deterministic local parsing is used.

The dashboard shows parser mode in Tactical Logs and in the `Program` tab under `Prompt-To-Drone Proof`.

## Install Ollama

Install Ollama from:

```text
https://ollama.com/download
```

Then pull the default model used by Shepherd-AI:

```bash
ollama pull gemma:2b
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

## Safety Boundary

The LLM never controls MAVSDK or PX4 directly. Its output is treated as intent JSON, then Shepherd-AI applies deterministic target resolution, fleet allocation, safety checks, and `SHEPHERD-IR` compilation before anything is dispatched.
