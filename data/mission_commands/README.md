# Mission Command Dataset

This directory contains early bilingual seed examples for future Shepherd-AI intent-parser training and evaluation.

The JSONL rows are research data, not an operational authority path. A model trained from this data may only produce bounded intent JSON; deterministic backend code still owns target resolution, allocation, safety, confirmation, SHEPHERD-IR compilation, and dispatch.

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
```

Export input/target rows for parser fine-tuning experiments:

```powershell
.\.venv\Scripts\python.exe -m backend.mission_dataset export
```

Evaluate the current offline parser baseline against the dataset:

```powershell
.\.venv\Scripts\python.exe -m backend.mission_dataset evaluate --summary-only
```

This is an evaluation scaffold, not model training. The current seed benchmark is also used by smoke tests to guard deterministic parser regressions before the dataset grows into a larger train/eval/holdout suite.
