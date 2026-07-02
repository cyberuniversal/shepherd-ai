# Colab Notebook Structure

These notebooks follow the roadmap order, but implementation details must follow `AGENTS.md` and `docs/literature_to_implementation.md`.

The notebooks are intentionally lightweight entry points. Shared logic should live in `src/shepherd_ai/` so experiments are reproducible from notebooks and scripts. Transformer fine-tuning belongs in Colab with a T4 GPU runtime; local machines should be used for lightweight validation, export, and tests.

Notebook sequence:

1. `Notebook1_Setup.ipynb` - environment setup, repository checks, source-document audit.
2. `Notebook2_NLP.ipynb` - command dataset, speech transcripts, intent extraction baselines/training.
3. `Notebook3_Grounding.ipynb` - map dataset loading and language-to-coordinate grounding.
4. `Notebook4_Planner.ipynb` - task decomposition and mission task graph.
5. `Notebook5_Scheduler.ipynb` - multi-drone allocation baselines.
6. `Notebook6_Vision.ipynb` - aerial image inference and detection summaries.
7. `Notebook7_Safety.ipynb` - deterministic safety validation and feedback.
8. `Notebook8_FinalDemo.ipynb` - integrated scenario demo.
9. `Notebook9_Evaluation.ipynb` - evaluation tables, figures, and research outputs.

Do not put private credentials, private audio, downloaded model weights, or undocumented datasets in notebooks.
