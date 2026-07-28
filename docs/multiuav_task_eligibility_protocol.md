# MultiUAV-Plat Task Eligibility And Alias Protocol

## Status

This protocol freezes source-task eligibility and one official alias per
retained task. It runs after the frozen session split and before any
missing-information or resource-conflict intervention is generated.

It is a leakage-control procedure, not a task-quality annotation.

## Source Binding

- Benchmark archive SHA-256:
  `b5040097d2bfdd44600f3bf486fdb43ee3eb1247fec9c67900b5fcda6feb94a3`
- Session split SHA-256:
  `988c6ac5662c0af21d71d883fe2c6a40f16afc4886cd49bbd5f674d45e893520`
- Eligibility seed: `shepherd-multiuav-eligibility-v1`
- Preserved manifest:
  `datasets/multiuav_plat/task_eligibility_v1.json`

## Canonical Ownership

For every normalized canonical instruction:

1. count its task occurrences in each split;
2. assign the instruction to the split with the greatest support;
3. break a support tie by ascending
   `sha256(seed + NUL + normalized_canonical + NUL + split)`; and
4. exclude occurrences in every non-owner split as complete source-task
   clusters.

Each task has one canonical instruction, so choosing the split with greatest
support independently minimizes canonical exclusions for the frozen session
split. Repeated canonical instructions within one split may remain because they
do not create cross-split leakage.

## Official Alias Eligibility

Alias candidates come only from the upstream `content_aliases` field. Reject a
candidate when its normalized text equals the task's canonical instruction or
a retained canonical instruction in another split.

For every remaining normalized alias:

1. count the distinct retained tasks it supports in each split;
2. assign the alias to the split with greatest support; and
3. break a support tie by ascending
   `sha256(seed + NUL + alias-owner + NUL + normalized_alias + NUL + split)`.

For each task, select the owned candidate with the lowest
`sha256(seed + NUL + task_id + NUL + normalized_alias)`. Source alias index
breaks a hash tie. A task with no owned alias is excluded as a complete cluster.

This rule is deterministic and favors retaining tasks supported by a shared
phrase. It is not a semantic quality ranking or a globally optimal
paraphrase-diversity objective.

## Frozen Result

- 1,500 source tasks inspected;
- 1,473 eligible source-task clusters;
- 27 excluded clusters, all due to cross-split canonical non-ownership;
- zero tasks excluded for lack of a nonleaking official alias;
- 899 retained train tasks;
- 290 retained calibration tasks;
- 284 retained test tasks;
- zero normalized canonical/selected-alias overlap across splits; and
- 7,365 prospective cases if every retained task later yields all five valid
  interventions.

The prospective split counts are 4,495 train, 1,450 calibration, and 1,420
test cases. These remain upper bounds until intervention construction and
review are complete.

## Claim Limits

This protocol does not establish that selected aliases preserve every task
nuance, that generated interventions will be valid, that 7,365 cases will
survive review, that any model can solve the tasks, or that static validation
equals official-server mission completion.

Selected aliases and subsequent interventions still require the registered
review and adjudication process before they become evaluation labels.
