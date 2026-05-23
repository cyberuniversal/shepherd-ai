# Mission Command Dataset

This directory contains bilingual examples for future Shepherd-AI intent-parser training and evaluation.

Important: the current JSONL files are synthetic research scaffolds generated for parser-contract tests, smoke tests, and early training experiments. They are not a public operational drone-command corpus and should not be presented as one. They are useful for verifying that Shepherd-AI preserves split handling, bounded intent JSON, clarification behavior, and promotion gates while the real dataset strategy matures.

The JSONL rows are research data, not an operational authority path. A model trained from this data may only produce bounded intent JSON; deterministic backend code still owns target resolution, allocation, safety, confirmation, SHEPHERD-IR compilation, and dispatch.

Files:

- `seed.jsonl`: compact smoke-test gate for known parser behavior.
- `benchmark.jsonl`: larger English/Arabic train/eval/holdout benchmark for parser evaluation and future model training.
- `targeted_augmentation.jsonl`: train-only English/Arabic examples added from parser failure-analysis categories. These rows may expand training corpora, but they are not an evaluation gate. The current file has 74 train-only rows focused on target aliases, Arabic target extraction, mission patterns, urgency wording, returns, and ambiguous-target handling.
- `adversarial_holdout.jsonl`: hard English/Arabic holdout commands for evaluation only. Do not tune the heuristic parser directly against this file; use it to measure whether parser changes generalize to ambiguous, contradictory, mixed, and under-specified commands.

Training data should teach slot extraction and bounded intent structure, not memorization of every possible place. Future public-data work should use general intent/slot datasets such as MASSIVE, SNIPS, CLINC150, or MTOP for language coverage, and separate gazetteer/map sources such as GeoNames or OpenStreetMap-derived local indexes for target resolution. Shepherd-specific rows should focus on command structure, target-span extraction, operator-relative references, counts, patterns, refusal/clarification behavior, and urgency signals.

The target-schema migration is two-phase. Phase 1 keeps legacy `target_zone` so existing parsers, reports, and frontend views remain compatible, while runtime code also carries `target_raw_text`, `target_type`, and `target_resolution_required`. Phase 2 should move training targets and evaluation metrics to a nested `target` object after compatibility and migration tests exist.

Priority is not a learned authority path. Dataset rows may include legacy `priority` values for compatibility with existing reports, but runtime planning computes final priority through `backend.priority` from explicit urgency language and deterministic mission policy. A model may help extract an urgency phrase in future schemas; it should not decide operational priority by memorizing labels.

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
.\.venv\Scripts\python.exe -m backend.mission_dataset validate --path data\mission_commands\targeted_augmentation.jsonl
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
.\.venv\Scripts\python.exe -m backend.learned_parser train-baseline --augmentation data\mission_commands\targeted_augmentation.jsonl --output .tmp_models\learned_parser_augmented.json --report .tmp_models\learned_parser_augmented_report.json
.\.venv\Scripts\python.exe -m backend.learned_parser evaluate --artifact .tmp_models\learned_parser_baseline.json --summary-only
```

Use `--augmentation` only for train-only rows. The loader appends those rows into the train split and keeps a separate `augmentation` report section for auditability; it does not move rows into eval, holdout, or adversarial gates.

Compare held-out behavior before and after augmentation:

```powershell
.\.venv\Scripts\python.exe -m backend.parser_comparison --baseline-artifact .tmp_models\learned_parser_baseline.json --candidate-artifact .tmp_models\learned_parser_augmented.json --output .tmp_models\parser_comparison.json --markdown .tmp_models\parser_comparison.md --summary-only
```

The default comparison scope is `eval`, `holdout`, and `adversarial`; train-only augmentation rows are excluded from the decision metric.

The optional transformer scaffold prepares the same frozen splits for PyTorch/transformer experiments:

```powershell
.\.venv\Scripts\python.exe -m backend.transformer_parser prepare --output-dir .tmp_models\transformer_parser\corpus
.\.venv\Scripts\python.exe -m backend.transformer_parser prepare --augmentation data\mission_commands\targeted_augmentation.jsonl --output-dir .tmp_models\transformer_parser_augmented\corpus
.\.venv\Scripts\python.exe -m backend.transformer_parser status
```

Analyze parser failures before adding new rows:

```powershell
.\.venv\Scripts\python.exe -m backend.parser_failure_analysis --report .tmp_models\learned_parser_report.json --output .tmp_models\parser_failure_analysis.json --markdown .tmp_models\parser_failure_analysis.md
```
