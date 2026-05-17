# Mission Command Dataset

This directory contains bilingual examples for future Shepherd-AI intent-parser training and evaluation.

The JSONL rows are research data, not an operational authority path. A model trained from this data may only produce bounded intent JSON; deterministic backend code still owns target resolution, allocation, safety, confirmation, SHEPHERD-IR compilation, and dispatch.

Files:

- `seed.jsonl`: compact smoke-test gate for known parser behavior.
- `benchmark.jsonl`: larger English/Arabic train/eval/holdout benchmark for parser evaluation and future model training.
- `adversarial_holdout.jsonl`: hard English/Arabic holdout commands for evaluation only. Do not tune the heuristic parser directly against this file; use it to measure whether parser changes generalize to ambiguous, contradictory, mixed, and under-specified commands.

Each row includes:

- `command`: the operator phrase.
- `expected_intent`: bounded parser JSON target.
- `expected_constraints`: deterministic backend constraints expected downstream.
- `split`: `train`, `eval`, or `holdout`.
- `should_clarify`: whether the parser should ask for target clarification.
- `notes`: short research context for the row.

Validate the seed set:

```powershell
.\.venv\Scripts\python.exe -m backend.mission_dataset validate
.\.venv\Scripts\python.exe -m backend.mission_dataset validate --path data\mission_commands\benchmark.jsonl
.\.venv\Scripts\python.exe -m backend.mission_dataset validate --path data\mission_commands\adversarial_holdout.jsonl
```

Export input/target rows for parser fine-tuning experiments:

```powershell
.\.venv\Scripts\python.exe -m backend.mission_dataset export
```

Evaluate the current offline parser baseline against the dataset:

```powershell
.\.venv\Scripts\python.exe -m backend.mission_dataset evaluate --summary-only
.\.venv\Scripts\python.exe -m backend.mission_dataset evaluate --path data\mission_commands\benchmark.jsonl --summary-only
.\.venv\Scripts\python.exe -m backend.mission_dataset evaluate --path data\mission_commands\benchmark.jsonl --report .tmp_scenarios\parser-eval.json --markdown-report .tmp_scenarios\parser-eval.md
.\.venv\Scripts\python.exe -m backend.mission_dataset evaluate --path data\mission_commands\adversarial_holdout.jsonl --report .tmp_scenarios\adversarial-eval.json --markdown-report .tmp_scenarios\adversarial-eval.md
```

This is an evaluation scaffold, not model training. The current seed set and benchmark are also used by smoke tests to guard deterministic parser regressions before training any learned parser. The adversarial holdout is validated and evaluated by smoke tests without accuracy thresholds so it remains an honest pressure test.

The learned-parser scaffold in `backend.learned_parser` trains only from benchmark `train` rows and evaluates `eval`, benchmark `holdout`, and `adversarial_holdout.jsonl` separately:

```powershell
.\.venv\Scripts\python.exe -m backend.learned_parser train-baseline --output .tmp_models\learned_parser_baseline.json --report .tmp_models\learned_parser_report.json
.\.venv\Scripts\python.exe -m backend.learned_parser evaluate --artifact .tmp_models\learned_parser_baseline.json --summary-only
```
