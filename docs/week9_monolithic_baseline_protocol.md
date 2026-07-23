# Week 9 Monolithic LLM Baseline Protocol

## Objective

Compare Shepherd-AI's modular evidence gates with a single-stage language model
that receives the same command and serialized stage evidence, then outputs one
decision: `proceed`, `clarify`, or `block`.

This is inference, not fine-tuning. The baseline must not receive gold labels,
Shepherd decisions, or hidden evaluation summaries.

## Primary Diagnostic Model

- Model: `Qwen/Qwen2.5-7B-Instruct`
- License recorded by the runner from the Hugging Face model card
- Loading: 4-bit NF4 with double quantization
- Compute dtype: float16
- Runtime: Google Colab NVIDIA T4
- Prompt: `shepherd_monolithic_decision_prompt_v1`
- Decoding: temperature `0.0`, one repetition, maximum 192 new tokens
- Seed: `17`
- Remote model code: disabled

The model is an accessible open-weight 7B instruction baseline, not a TACOS
reimplementation. The official model card and Hugging Face quantization
documentation support Transformers chat templates and 4-bit loading:

- <https://huggingface.co/Qwen/Qwen2.5-7B-Instruct>
- <https://huggingface.co/docs/transformers/main/quantization/bitsandbytes>
- <https://huggingface.co/docs/transformers/chat_templating>

The runner resolves `main` to an exact Hugging Face commit SHA before loading
and records that SHA. A later rerun must use the recorded commit rather than
assuming that `main` is unchanged.

## Leakage Controls

`scripts/build_monolithic_decision_packet.py` writes:

- label-free inference inputs to
  `outputs/evaluations/week9_monolithic_diagnostic_inputs_v1.jsonl`;
- separated labels to
  `datasets/evidence/week9_monolithic_diagnostic_gold_v1.jsonl`; and
- source and prompt hashes to
  `outputs/evaluations/week9_monolithic_diagnostic_manifest_v1.json`.

The model runner accepts only the input JSONL. It validates every prompt hash
and rejects records containing `expected_decision`, `shepherd_decision`, or
`gold_label`.

## Colab/T4 Procedure

From a fresh Colab T4 runtime:

```bash
!git clone --branch codex/evidence-aware-paper \
  https://github.com/cyberuniversal/shepherd-ai.git
%cd /content/shepherd-ai
!python -m pip install -e .
!python -m pip install \
  "transformers>=4.48,<5" \
  "accelerate>=1.2,<2" \
  "bitsandbytes>=0.45,<1" \
  "huggingface_hub>=0.27,<1"
```

Regenerate and verify the label-separated packet:

```bash
!python scripts/evaluate_evidence_aware_decisions.py
!python scripts/build_monolithic_decision_packet.py
```

Run the frozen baseline:

```bash
!python scripts/run_hf_monolithic_decision_baseline.py \
  --required-device-substring T4 \
  --precision 4bit \
  --temperature 0 \
  --repetitions 1 \
  --seed 17
```

The runner checkpoints the JSON after every case. If Colab disconnects, rerun
the same command with `--resume`. Resume is refused when the input hash, model
commit, prompt version, precision, or decoding parameters differ.

Only after inference completes, score the raw output:

```bash
!python scripts/evaluate_monolithic_decision_baseline.py
```

Download or commit the raw and derived JSON before the Colab runtime is
released.

## Required Stored Artifacts

- Exact label-free input JSONL and SHA-256
- Separate gold JSONL and SHA-256
- Packet manifest
- Raw model responses, including invalid responses
- Requested model name and resolved commit SHA
- Model license, package versions, device name, quantization, parameters, and
  seeds
- Per-case generation time and prompt hash
- Derived comparison JSON and report

## Fresh Human-Held-Out Requirement

The current 38-case packet reuses existing development evidence and is only a
diagnostic. A final paper comparison requires a separately collected,
adjudicated human benchmark that passes
`scripts/validate_human_evidence_benchmark.py`.

The final benchmark must:

- keep author and reviewer identities pseudonymous and distinct;
- keep model-generated commands out of the human-written data type;
- avoid normalized text overlap with existing command datasets;
- balance `proceed`, `clarify`, and `block`;
- freeze contexts and labels before baseline inference; and
- remain untouched while errors are analyzed on development data.

## Interpretation

Invalid JSON is an error and is never manually repaired. A `proceed` decision
on a gold `clarify` or `block` case counts as a silent-misexecution proxy, not
an observed physical misexecution. No result from this protocol establishes
physical safety or real-world reliability.
