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

Train a local seq2seq transformer experiment:

```powershell
.\.venv\Scripts\python.exe -m backend.transformer_parser train --corpus-dir .tmp_models\transformer_parser\corpus --output-dir .tmp_models\transformer_parser\model --base-model google/mt5-small --epochs 3 --batch-size 2
```

Run bounded prediction from the trained model:

```powershell
.\.venv\Scripts\python.exe -m backend.transformer_parser predict "Send two drones to KAFD" --model-dir .tmp_models\transformer_parser\model
```

The transformer adapter parses generated JSON, coerces it through the bounded intent contract, marks `needs_confirmation=true`, and never returns dispatch commands.
