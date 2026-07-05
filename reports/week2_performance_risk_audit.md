# Week 2 Performance Risk Audit

Performance-risk audit only. These findings explain why current Week 2 metrics can be high; they do not invalidate the artifacts, but they limit claim strength.

## Why It Looks Good

- The current command language is short, schema-like, and close to the known Week 2 fields.
- All currently evaluated audio transcripts match commands already present in the curated text and span datasets.
- The ASR sample is clean and tiny, so one substitution dominates the measured speech error.
- The strongest intent model is hybrid: it uses deterministic rule overrides for action, location, target, count, and constraints.
- The expanded span dataset includes targeted follow-up records derived from earlier error analysis, which can improve known failure modes.
- The held-out span test split has only 10 records, so each record has large influence on F1.

## Evidence Profile

- Intent command records: 50 with splits `{"test": 10, "train": 30, "validation": 10}`.
- Span command records: 85 with splits `{"test": 10, "train": 57, "validation": 18}`.
- Audio records: 10 with splits `{"test": 2, "train": 6, "validation": 2}`.
- Audio transcripts matching curated command records: 10 / 10.
- Audio transcripts matching span records: 10 / 10.
- Duplicate command texts across splits: 0.
- Duplicate span texts across splits: 0.
- Intent model uses rule overrides: `True`.

## Risk Factors

- **high** `small_audio_sample`: Only 10 audio records are evaluated.
- **medium** `small_intent_dataset`: Only 50 curated intent records exist.
- **medium** `small_span_dataset`: Only 85 span records exist.
- **high** `retrospective_audio_split`: The current status summary notes a retrospective audio split, so ASR split metrics are not a clean final benchmark.
- **high** `audio_text_overlap`: Every audio transcript matches at least one curated command-label record.
- **medium** `audio_span_overlap`: Every audio transcript matches at least one human-verified span record.
- **medium** `assistant_curated_intent_labels`: The curated intent labels are assistant-curated from user text, not independently human-adjudicated labels.
- **medium** `hybrid_intent_model`: The strongest intent model uses deterministic rule overrides, so its score is not a pure learned-model result.
- **medium** `targeted_span_followup`: The expanded span dataset includes targeted follow-up records derived from earlier model errors.

## Stronger Next Evidence

- Collect a larger pre-registered audio batch before running ASR.
- Use commands that do not overlap existing training, validation, or test texts.
- Preserve human labels from at least one reviewer instead of assistant-curated labels only.
- Evaluate the Colab/T4 transformer checkpoint directly on human transcripts and ASR transcripts once checkpoint artifacts are restored.
- Create a fresh held-out span test set after targeted follow-up data collection.

## Source Artifacts

- `commands`: `datasets\commands\human_written_commands_curated_v1.jsonl`
- `spans`: `datasets\commands\human_verified_span_commands.jsonl`
- `audio_manifest`: `datasets\sample_audio\manifest.jsonl`
- `status_summary`: `outputs\evaluations\week2_status_summary.json`
- `intent_model`: `outputs\model_artifacts\intent_nb_human_curated_v2.json`
