# MultiUAV External Manuscript Review Protocol

## Purpose

The active MultiUAV validation-placement study has passed its internal
artifact and claim-boundary audit. External review is required to challenge
the scientific framing, methods, statistics, interpretation, and related-work
positioning. It must not be replaced by an automated approval or a fabricated
reviewer identity.

## Review Artifact

The review target is
`reports/multiuav_validation_placement_manuscript_v1.md`. The packet generator
binds the exact manuscript, internal traceability audit, source tables, and
figure manifests by SHA-256. A changed manuscript requires a new packet and a
new review round.

## Reviewer Requirements

The reviewer should have relevant experience in at least one of robotics,
multi-agent systems, language-model evaluation, experimental design, or
statistical analysis. The project records a pseudonymous reviewer identifier,
declared expertise, and conflict statement. A name, degree, affiliation, or
independence claim must not be invented.

The reviewer is not asked to approve individual benchmark labels. This review
concerns the paper-level argument and whether the evidence supports it.

## Required Questions

1. Is the stated contribution bounded and distinguishable from the cited
   systems without claiming that validation or refusal is individually new?
2. Are M1-M4 described accurately, especially the limit that M4 is matched to
   M3 only by model-call count?
3. Are the five paired variants and source-task-cluster statistical unit
   justified and understandable?
4. Are unsafe proceed and strict end-to-end success valid operationalizations
   for the stated research questions?
5. Is the mixed 3B/7B result interpreted without cherry-picking?
6. Are resource outcomes kept secondary, repetition-specific, and
   hardware-scoped?
7. Are interval estimates described without turning them into unregistered
   null-hypothesis tests?
8. Are the static-fidelity, controlled-derivative, within-Qwen, network,
   hardware, and protocol-deviation limitations sufficiently prominent?
9. Does the related-work section omit a close comparison or misstate a cited
   system?
10. What claims, figures, tables, or wording must change before submission?

## Required Response Structure

The reviewer returns a separate UTF-8 Markdown or PDF file containing:

- reviewer pseudonym and expertise;
- conflict-of-interest declaration;
- overall assessment: accept as internally defensible, minor revision, major
  revision, or not supportable from current evidence;
- numbered findings with severity, manuscript section, and rationale;
- required corrections;
- optional improvements; and
- explicit confirmation of whether the abstract and conclusion match the
  reported results.

The project owner preserves the original review, creates a response-to-review
ledger, and links every accepted correction to a commit. Rejected suggestions
remain recorded with a reason. Review completion does not imply venue
acceptance or physical-safety validation.

## Completion Gate

External review passes only after a real response is preserved, all required
findings are resolved or explicitly rebutted, the reviewer packet hash matches
the reviewed manuscript, and a response ledger passes a separate audit.
