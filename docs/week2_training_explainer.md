# Week 2 Training Explainer

## What Is Being Trained

The current Week 2 trained component is a supervised text intent extractor. It predicts three fields from a command:

- `action`
- `location`
- `target`

The current model does not train `count` or `constraints`. Those fields still come from deterministic extraction rules in `src/shepherd_ai/intent.py`.

## Current Model Family

The current model is field-level multinomial Naive Bayes:

- One classifier predicts `action`.
- One classifier predicts `location`.
- One classifier predicts `target`.

Each classifier learns token counts per label from labeled examples in the `train` split. At prediction time, it computes which label is most likely for the command text under the learned word/feature counts.

This is classical supervised machine learning, not neural fine-tuning.

## Why Start With Naive Bayes

Naive Bayes is intentionally simple:

- It is inspectable.
- It works with tiny datasets.
- It creates a real trained baseline before adding larger dependencies.
- It is fast enough for unit tests and Colab.
- It makes data, split, and evaluation bugs visible early.

The literature review supports using bounded, inspectable representations and keeping learned language interpretation separated from execution. This baseline follows that idea by producing a structured intent record rather than executable code.

## Why Deterministic Parsing Is Not Enough

The literature review supports deterministic validation and safety gating, but it does not support treating a hand-written parser as the whole language-understanding system. TACOS, Swarm-Steward, CommandSwarm, the natural-language-to-PDDL paper, and PROGPROMPT all point toward a separation between language interpretation and execution authority.

The immediate Shepherd-AI consequence is:

- Deterministic code should validate schemas, block unsafe or unsupported commands, and protect later planning/scheduling modules.
- The semantic interpretation layer still needs training, fine-tuning, or another evaluated language method when enough labeled data exists.
- Parser results are baselines and draft labels unless a human verifies them.
- Parser coverage failures are real negative results, not cases to hide by silently expanding examples.

## Feature Sets

`trained_nb_v0` uses:

- Unigram word features.

`trained_nb_v1` uses:

- Unigram word features.
- Bigram features such as adjacent word pairs.
- Field-specific schema-alias features derived from the bounded Week 2 schema.

Schema-alias features are not free-form reasoning. They encode known aliases such as `north`/`northern`, `greenhouse`, and `irrigation canal` as features that a supervised classifier can use.

`deterministic_v1` also includes an open-vocabulary target phrase fallback. If no bounded target alias matches, it can extract short target phrases for supported actions such as `inspect`, `scan`, `capture`, and `search`. This reduces brittleness for commands like "inspect the livestock pen" or "capture images of the red pickup truck," but it is still deterministic and still needs held-out evaluation.

## Training Flow

1. Load JSONL command records from `datasets/commands/intent_labeled_synthetic.jsonl`.
2. Validate required fields and reject duplicate command text across splits.
3. Select only `split == "train"` for fitting.
4. Train separate classifiers for `action`, `location`, and `target`.
5. Save the model artifact under `outputs/model_artifacts/`.
6. Evaluate on validation and test records.
7. Save raw metrics under `outputs/evaluations/`.
8. Compare against the deterministic parser baseline.

## What The Metrics Mean

Field accuracy counts each individual intent field match.

Exact-record accuracy counts a record as correct only if all evaluated fields match.

Field-level error counts show where the model failed, for example whether errors are concentrated in `location`.

The current `1.0` result for `trained_nb_v1` is only on a four-record synthetic validation split and a four-record synthetic test split. It is a workflow check, not evidence of real-world performance.

## What Comes Next

The next meaningful Week 2 improvement is not a more complicated model by itself. The project needs real data:

- Human-written commands.
- Recorded WAV commands.
- Human-verified transcripts.
- ASR transcripts from a documented Whisper configuration.

After that, a spaCy or Hugging Face model can be trained or fine-tuned if the dataset is large enough to justify it. Transformer fine-tuning should run in Google Colab with a T4 GPU runtime; local CPU training is not the supported Week 2 path.

## Papers To Read First

From the repository literature review, read these first:

1. `#8, CommandSwarm Safety-Aware Natural Language-to-...`
   - Most relevant for speech/Whisper, safety-aware language-to-swarm structure, validation, and the danger of treating language output as directly executable.

2. `#1, TACOS Task Agnostic Coordinator of a Multi-Dro...`
   - Relevant for separating high-level natural-language coordination from lower-level execution.

3. `#2, Swarm-Steward Scalable and Reliable Natural-La...`
   - Relevant for scalable language interfaces to multi-robot systems and the need for reliability checks.

4. `#3, Say the Mission, Execute the Swarm Agent-Enhan...`
   - Relevant for natural-language mission interfaces and agent-enhanced swarm execution.

5. `#7, Translating Natural Language to Planning Goals...`
   - Relevant for converting language into bounded planning goals rather than arbitrary code.

6. `#13, PROGPROMPT Generating Situated Robot Task Pla...`
   - Relevant for structured intermediate programs/plans and why validation matters.

7. `#14, GenSwarm Scalable Multi-Robot Code-Policy Gen...`
   - Relevant for multi-robot code-policy generation, while also motivating why Shepherd-AI should validate outputs before execution.

8. `#10, Towards Natural Language-Guided Drones GeoTex...`
   - Relevant later for language grounding in aerial imagery, not as proof that Week 2 intent extraction is solved.

9. `#9, Visual Language Maps for Robot Navigation`
   - Relevant later for semantic grounding, especially the limits of mapping language to spatial targets.

10. `#12, Comparative Analysis of Centralized and Distr...`
    - Relevant later for task allocation baselines, not Week 2 training directly.

Read each paper page together with its `Complete Summary ...md` file in the literature-review export.
