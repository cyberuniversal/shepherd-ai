# Learned Parser Research Scaffold

This is the first training scaffold for Shepherd-AI intent parsing. It is not connected to live dispatch. A learned parser artifact may only produce bounded intent JSON; deterministic backend code still owns target resolution, allocation, safety checks, confirmation, SHEPHERD-IR compilation, and MAVSDK/MAVLink dispatch.

## Current Baseline

The current baseline is `nearest_ngram_intent`, a dependency-light offline model that stores train-split examples from `data/mission_commands/benchmark.jsonl` and predicts by nearest text features. It exists to prove the training/evaluation pipeline, artifact format, split handling, augmentation handling, and strict output adapter before heavier PyTorch or transformer work.

The adversarial holdout file is evaluation-only. It is loaded into reports, but its rows are not stored in the trained artifact.

`data/mission_commands/targeted_augmentation.jsonl` is train-only failure-analysis data. It may be appended to the train split with `--augmentation`, but it is not a promotion gate and must not be mixed into eval, holdout, or adversarial rows.

## Train

```powershell
.\.venv\Scripts\python.exe -m backend.learned_parser train-baseline --output .tmp_models\learned_parser_baseline.json --report .tmp_models\learned_parser_report.json
.\.venv\Scripts\python.exe -m backend.learned_parser train-baseline --augmentation data\mission_commands\targeted_augmentation.jsonl --output .tmp_models\learned_parser_augmented.json --report .tmp_models\learned_parser_augmented_report.json
```

Outputs under `.tmp_models/` are local research artifacts and are ignored by git.

## Evaluate

```powershell
.\.venv\Scripts\python.exe -m backend.learned_parser evaluate --artifact .tmp_models\learned_parser_baseline.json --summary-only
```

The report includes train, eval, benchmark holdout, and adversarial holdout metrics. `adversarial_used_for_training` must remain `false`.

When `--augmentation` is used, the report also includes `augmentation_count` and an `augmentation` split report for traceability. Training still happens through the train split; the extra report section only proves which failure-analysis rows were added.

## Promotion Gate

Run the parser promotion gate before treating any learned artifact as a candidate for runtime integration:

```powershell
.\.venv\Scripts\python.exe -m backend.parser_promotion --artifact .tmp_models\learned_parser_baseline.json --report .tmp_models\parser_promotion_gate.json
```

The command exits nonzero when the artifact fails threshold or contract checks. For research reporting without failing the shell command:

```powershell
.\.venv\Scripts\python.exe -m backend.parser_promotion --artifact .tmp_models\learned_parser_baseline.json --report .tmp_models\parser_promotion_gate.json --allow-failure
```

The current nearest-ngram baseline is expected to fail promotion. It exists to prove the scaffold, not to replace the bounded heuristic or LLM parser.

After training a transformer model, evaluate that model directory with the same gate:

```powershell
.\.venv\Scripts\python.exe -m backend.parser_promotion --candidate-type transformer-model --model-dir .tmp_models\transformer_parser\model --report .tmp_models\transformer_parser\promotion_gate.json
```

Transformer promotion requires the trained model directory to contain `shepherd_model_contract.json`, optional training dependencies to be installed, all predictions to pass through the bounded-intent adapter, and split provenance proving the adversarial holdout was not used for training.

## Optional Runtime Use

The backend can optionally use a promoted learned parser artifact at runtime. This is disabled by default. Runtime loading requires both the artifact and a promotion report that says `promoted=true`, matches the artifact digest, and passes the bounded-intent contract checks.

```powershell
$env:SHEPHERD_ENABLE_LEARNED_PARSER="1"
$env:SHEPHERD_LEARNED_PARSER_ARTIFACT=".tmp_models\learned_parser_augmented.json"
$env:SHEPHERD_LEARNED_PARSER_PROMOTION_REPORT=".tmp_models\parser_promotion_augmented_gate.json"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Equivalent selector:

```powershell
$env:SHEPHERD_PARSER_RUNTIME="learned"
```

To audit a promoted learned parser without making it the active parser:

```powershell
$env:SHEPHERD_SHADOW_LEARNED_PARSER="1"
```

Shadow mode loads the same promotion-validated artifact, keeps the existing parser active, and records field-level active-vs-shadow comparisons in parser status and mission parser summaries.

Summarize shadow comparisons from signed evidence:

```powershell
.\.venv\Scripts\python.exe -m backend.parser_shadow_report --report .tmp_scenarios\parser-shadow-report.json
curl "http://localhost:8000/api/research/parser-shadow-report?include_records=false"
```

Export review-required augmentation candidates from disagreements:

```powershell
.\.venv\Scripts\python.exe -m backend.parser_shadow_candidates --output .tmp_scenarios\parser-shadow-candidates.jsonl --summary-only
curl "http://localhost:8000/api/research/parser-shadow-candidates"
```

These candidates are not training data. They set `ready_for_training=false` and preserve both active and shadow intent options so the expected intent can be manually selected or corrected before any row is added to `data/mission_commands/targeted_augmentation.jsonl`.

After review, convert approved candidates into dataset-compatible train rows:

```powershell
.\.venv\Scripts\python.exe -m backend.parser_shadow_review --input .tmp_scenarios\parser-shadow-candidates.reviewed.jsonl --output .tmp_scenarios\reviewed-shadow-augmentation.jsonl
```

Approved statuses are `approved_active`, `approved_shadow`, and `manual_corrected`. Unreviewed candidates are skipped. `manual_corrected` rows must include an explicit `expected_intent` object.

If the artifact, digest, candidate path, promotion report, or contract is invalid, Shepherd-AI fails closed to the existing Ollama/heuristic parser path. The learned parser still returns only bounded intent JSON. Plan-first confirmation, target resolution, safety checks, SHEPHERD-IR compilation, runtime assurance, and MAVSDK/MAVLink dispatch remain deterministic backend responsibilities.

## Failure Analysis

Generate a grouped failure analysis after any full evaluation report:

```powershell
.\.venv\Scripts\python.exe -m backend.parser_failure_analysis --report .tmp_models\learned_parser_report.json --output .tmp_models\parser_failure_analysis.json --markdown .tmp_models\parser_failure_analysis.md
```

Or evaluate and analyze a learned artifact in one step:

```powershell
.\.venv\Scripts\python.exe -m backend.parser_failure_analysis --artifact .tmp_models\learned_parser_baseline.json --output .tmp_models\parser_failure_analysis.json --markdown .tmp_models\parser_failure_analysis.md
```

The report groups misses by split, language, failed field, confusion pair, command category, and highest-risk examples. Use it to decide which dataset rows to add next.

## Baseline Comparison

After adding train-only augmentation, compare the original and augmented artifacts against the same held-out rows:

```powershell
.\.venv\Scripts\python.exe -m backend.parser_comparison --baseline-artifact .tmp_models\learned_parser_baseline.json --candidate-artifact .tmp_models\learned_parser_augmented.json --output .tmp_models\parser_comparison.json --markdown .tmp_models\parser_comparison.md --summary-only
```

The comparison scope defaults to `eval`, `holdout`, and `adversarial`. It reports subset-accuracy deltas, field deltas, language deltas, held-out improvements, and regressions. It intentionally excludes the augmentation split from the default comparison because those rows are training evidence, not an evaluation gate.

## Predict

```powershell
.\.venv\Scripts\python.exe -m backend.learned_parser predict "Send two drones to KAFD" --artifact .tmp_models\learned_parser_baseline.json
```

The strict adapter returns only bounded intent fields:

- action
- target zone/reference
- drone count
- priority
- pattern
- confirmation requirement
- confidence and clarification question
- parser/model provenance

It never returns MAVSDK commands, vehicle actuation calls, or dispatch authority.

The adapter also applies deterministic intent-slot normalization before final coercion. Known landmark aliases, coordinates, home/current-position commands, operator-relative phrasing, unresolved deictic targets, explicit action verbs, mission patterns, priority words, and explicit drone counts are normalized into bounded intent fields. This is not learned dispatch logic; it is a conservative parser-side guard that keeps obvious command slots from depending on nearest-neighbor text similarity.

## Next Research Step

The next model step can run the optional transformer trainer behind the same artifact/report contract:

1. Train only on benchmark `train` rows.
2. Tune only against benchmark `eval` rows.
3. Report benchmark `holdout` and `adversarial_holdout.jsonl` separately.
4. Keep the strict adapter as the production-facing boundary.
5. Pass the parser promotion gate before any runtime integration is considered.
6. Use failure analysis and baseline-vs-augmented comparisons to drive dataset growth rather than tuning against the adversarial holdout directly.

## Transformer Scaffold

Prepare frozen corpora for PyTorch/transformer training:

```powershell
.\.venv\Scripts\python.exe -m backend.transformer_parser prepare --output-dir .tmp_models\transformer_parser\corpus
.\.venv\Scripts\python.exe -m backend.transformer_parser prepare --augmentation data\mission_commands\targeted_augmentation.jsonl --output-dir .tmp_models\transformer_parser_augmented\corpus
```

Check optional training dependencies:

```powershell
.\.venv\Scripts\python.exe -m backend.transformer_parser status
```

Install optional training dependencies only on a machine intended for model work:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-train.txt
```

On Windows, `pip install torch` may install a CPU-only wheel. For NVIDIA GPU training, install the official CUDA wheel after the normal training requirements:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade --force-reinstall torch --index-url https://download.pytorch.org/whl/cu126
.\.venv\Scripts\python.exe -m backend.transformer_parser status
```

The status command reports `hardware.cuda_available`, CUDA runtime version, visible GPU names, total/free VRAM, and whether a low-VRAM profile is recommended.

Train a local seq2seq transformer experiment:

```powershell
.\.venv\Scripts\python.exe -m backend.transformer_parser train --corpus-dir .tmp_models\transformer_parser\corpus --output-dir .tmp_models\transformer_parser\model --base-model google/mt5-small --epochs 3 --batch-size 2
```

For a 4 GB GPU such as a GTX 1650 Super, start with a low-VRAM probe:

```powershell
.\.venv\Scripts\python.exe -m backend.transformer_parser train --corpus-dir .tmp_models\transformer_parser_prefixed\corpus --output-dir .tmp_models\transformer_parser_prefixed\model_gpu_probe --base-model "google/mt5-small" --epochs 0.1 --batch-size 1 --gradient-accumulation-steps 4 --gradient-checkpointing --optim adafactor --max-source-length 128 --max-target-length 192
```

Training examples are prefixed with an explicit extraction instruction before tokenization. The raw operator command is still preserved in the corpus as `raw_command`. The trainer saves only the final local candidate by default because checkpoint copies can consume multiple gigabytes; add `--save-checkpoints` only when checkpoint inspection is required.

Run bounded prediction from the trained model:

```powershell
.\.venv\Scripts\python.exe -m backend.transformer_parser predict "Send two drones to KAFD" --model-dir .tmp_models\transformer_parser\model
```

The transformer adapter parses generated JSON, coerces it through the bounded intent contract, marks `needs_confirmation=true`, and never returns dispatch commands.
Transformer outputs are labeled with `parser=transformer_seq2seq` after bounded coercion so shadow reports and promotion reports can distinguish them from the nearest-ngram baseline.

Inspect raw generations before making dataset or model changes:

```powershell
.\.venv\Scripts\python.exe -m backend.transformer_parser predict "Send two drones to KAFD" --model-dir .tmp_models\transformer_parser\model --show-raw
.\.venv\Scripts\python.exe -m backend.transformer_parser diagnose --model-dir .tmp_models\transformer_parser\model --corpus-dir .tmp_models\transformer_parser\corpus --split eval --limit 20 --output .tmp_models\transformer_parser\generation-diagnostics.json
```

The diagnostic report records raw generated text, raw JSON validity, bounded adapter output, expected intent, field-by-field matches, and common raw generations. It is a research report only; runtime dispatch still depends on promotion-gated bounded intent plus deterministic backend safety.

## First Transformer Training Probe

The first end-to-end PyTorch/transformer probe was run on CPU with the augmented corpus:

```powershell
.\.venv\Scripts\python.exe -m backend.transformer_parser prepare --augmentation data\mission_commands\targeted_augmentation.jsonl --output-dir .tmp_models\transformer_parser_augmented\corpus
.\.venv\Scripts\python.exe -m backend.transformer_parser train --corpus-dir .tmp_models\transformer_parser_augmented\corpus --output-dir .tmp_models\transformer_parser_augmented\model_cpu_probe --base-model "google/mt5-small" --epochs 0.1 --batch-size 1
.\.venv\Scripts\python.exe -m backend.parser_promotion --candidate-type transformer-model --model-dir .tmp_models\transformer_parser_augmented\model_cpu_probe --report .tmp_models\transformer_parser_augmented\promotion_gate_cpu_probe.json --allow-failure
```

Result: the training path, model contract, bounded adapter, and promotion gate all ran successfully. The short CPU probe is not promoted: eval subset accuracy was `0.0`, holdout subset accuracy was `0.0`, and adversarial subset accuracy was `0.1`. Treat it as infrastructure proof, not as a usable parser. A real candidate needs a longer GPU-backed run and should still pass the same promotion gate before runtime use.

## CPU 1-Epoch Transformer Candidate

A one-epoch CPU run with the explicit task prefix and train-only targeted augmentation completed successfully:

```powershell
.\.venv\Scripts\python.exe -m backend.transformer_parser prepare --augmentation data\mission_commands\targeted_augmentation.jsonl --output-dir .tmp_models\transformer_parser_prefixed\corpus
.\.venv\Scripts\python.exe -m backend.transformer_parser train --corpus-dir .tmp_models\transformer_parser_prefixed\corpus --output-dir .tmp_models\transformer_parser_prefixed\model_cpu_1epoch --base-model "google/mt5-small" --epochs 1 --batch-size 1
.\.venv\Scripts\python.exe -m backend.parser_promotion --candidate-type transformer-model --model-dir .tmp_models\transformer_parser_prefixed\model_cpu_1epoch --report .tmp_models\transformer_parser_prefixed\promotion_gate_cpu_1epoch.json --allow-failure
```

Result: the candidate is contract-valid and produced `100%` bounded outputs, but it is not promoted. Eval subset accuracy is `0.0`, holdout subset accuracy is `0.0`, and adversarial subset accuracy is `0.1`. Field-level metrics show partial learning on action extraction (`0.905` eval action accuracy), but target, pattern, and drone-count extraction remain too weak for runtime use. Keep this as a training milestone and failure-analysis input, not a deployed parser.

## GTX 1650 Super GPU Probe

CUDA training was verified on a Windows GTX 1650 Super after replacing CPU-only PyTorch with `torch 2.12.0+cu126`. The status command reported CUDA available, CUDA runtime `12.6`, one `NVIDIA GeForce GTX 1650 SUPER`, and `4095.6` MiB VRAM.

Two 0.1-epoch GPU probes were run:

```powershell
.\.venv\Scripts\python.exe -m backend.transformer_parser train --corpus-dir .tmp_models\transformer_parser_prefixed\corpus --output-dir .tmp_models\transformer_parser_prefixed\model_gpu_probe --base-model "google/mt5-small" --epochs 0.1 --batch-size 1 --gradient-accumulation-steps 4 --fp16 --gradient-checkpointing --optim adafactor --max-source-length 128 --max-target-length 192
.\.venv\Scripts\python.exe -m backend.transformer_parser train --corpus-dir .tmp_models\transformer_parser_prefixed\corpus --output-dir .tmp_models\transformer_parser_prefixed\model_gpu_probe_fp32 --base-model "google/mt5-small" --epochs 0.1 --batch-size 1 --gradient-accumulation-steps 4 --gradient-checkpointing --optim adafactor --max-source-length 128 --max-target-length 192
```

Result: the FP16 probe completed without CUDA OOM but produced `eval_loss=nan`, so it should not be used as the default GTX 1650 Super profile. The FP32 probe completed without CUDA OOM and produced finite `eval_loss=12.95`; the promotion gate again confirmed `100%` bounded outputs but did not promote the candidate. The reliable local profile for this 4 GB GPU is therefore FP32 + Adafactor + gradient checkpointing + batch size `1` + gradient accumulation. The generated probe model directories were removed after reporting because they are ignored, multi-GB, and not promoted.

## GPU 1-Epoch Raw Generation Finding

A one-epoch GTX 1650 Super run with the stable low-VRAM profile completed in roughly two minutes:

```powershell
.\.venv\Scripts\python.exe -m backend.transformer_parser train --corpus-dir .tmp_models\transformer_parser_prefixed\corpus --output-dir .tmp_models\transformer_parser_prefixed\model_gpu_fp32_1epoch --base-model "google/mt5-small" --epochs 1 --batch-size 1 --gradient-accumulation-steps 4 --gradient-checkpointing --optim adafactor --max-source-length 128 --max-target-length 192
.\.venv\Scripts\python.exe -m backend.transformer_parser diagnose --model-dir .tmp_models\transformer_parser_prefixed\model_gpu_fp32_1epoch --corpus-dir .tmp_models\transformer_parser_prefixed\corpus --split eval --limit 12 --output .tmp_models\transformer_parser_prefixed\diagnostics_gpu_fp32_1epoch_eval12.json
.\.venv\Scripts\python.exe -m backend.parser_promotion --candidate-type transformer-model --model-dir .tmp_models\transformer_parser_prefixed\model_gpu_fp32_1epoch --report .tmp_models\transformer_parser_prefixed\promotion_gate_gpu_fp32_1epoch.json --allow-failure
```

Result: the run produced finite `eval_loss=12.12`, stayed within local GPU limits, and again passed bounded-output contract checks, but it was not promoted. Raw diagnostics showed the central model-quality failure: generations were mostly mT5 sentinel text such as `<extra_id_0>` rather than JSON. On the first 12 eval rows, raw JSON validity was `0/12`, bounded output validity was `12/12`, action accuracy was `1.0`, drone-count accuracy was `0.5`, pattern accuracy was `0.0`, and target-zone accuracy was `0.0`. The bounded adapter is therefore correctly failing closed; the next research step is to change the training objective/output format or model choice so the model learns to emit JSON before running longer or larger jobs.
