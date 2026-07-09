# Week 2 Completion Criteria

Scope: clean post-development speech and intent benchmark for Week 2.

This gate exists because the current Week 2 handoff is useful but provisional. It must not be treated as final research evidence until a fresh, non-overlapping benchmark exists after the current parser/model state.

Required:

- Current Week 2 ASR status exists.
- Bounded intent JSON fields are documented: `action`, `count`, `location`, `target`, `constraints`.
- At least one trained language component is recorded.
- Known Week 2 risks are documented.
- The current handoff explicitly says it is not final.
- A fresh post-development audio manifest has at least 30 records.
- The fresh manifest has zero transcript overlap with prior command, span, or audio text.
- The fresh manifest has zero duplicate transcripts inside the candidate batch.
- Fresh audio-intent labels are human-reviewed and ready for gold evaluation.
- Fresh ASR evaluation exists for the full fresh batch.
- Fresh intent evaluation exists for at least three systems or paths.
- Transformer negative results remain preserved instead of hidden.

This gate does not require perfect accuracy. It requires clean evidence, fixed splits, human-reviewed labels, provenance, and honest negative-result preservation.
