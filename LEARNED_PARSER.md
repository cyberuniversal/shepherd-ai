# Learned Parser Research Scaffold

This is the first training scaffold for Shepherd-AI intent parsing. It is not connected to live dispatch. A learned parser artifact may only produce bounded intent JSON; deterministic backend code still owns target resolution, allocation, safety checks, confirmation, SHEPHERD-IR compilation, and MAVSDK/MAVLink dispatch.

## Current Baseline

The current baseline is `nearest_ngram_intent`, a dependency-light offline model that stores train-split examples from `data/mission_commands/benchmark.jsonl` and predicts by nearest text features. It exists to prove the training/evaluation pipeline, artifact format, split handling, and strict output adapter before heavier PyTorch or transformer work.

The adversarial holdout file is evaluation-only. It is loaded into reports, but its rows are not stored in the trained artifact.

## Train

```powershell
.\.venv\Scripts\python.exe -m backend.learned_parser train-baseline --output .tmp_models\learned_parser_baseline.json --report .tmp_models\learned_parser_report.json
```

Outputs under `.tmp_models/` are local research artifacts and are ignored by git.

## Evaluate

```powershell
.\.venv\Scripts\python.exe -m backend.learned_parser evaluate --artifact .tmp_models\learned_parser_baseline.json --summary-only
```

The report includes train, eval, benchmark holdout, and adversarial holdout metrics. `adversarial_used_for_training` must remain `false`.

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

## Next Research Step

The next model step can add a PyTorch or transformer trainer behind the same artifact/report contract:

1. Train only on benchmark `train` rows.
2. Tune only against benchmark `eval` rows.
3. Report benchmark `holdout` and `adversarial_holdout.jsonl` separately.
4. Keep the strict adapter as the production-facing boundary.
