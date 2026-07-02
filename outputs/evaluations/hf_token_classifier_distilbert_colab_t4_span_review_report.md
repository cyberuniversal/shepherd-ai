# Week 2 Span Review Commands

This file is a review aid. The command file starts from the current gold spans, and model predictions are not gold labels.

- Span dataset: `datasets/commands/human_verified_span_commands.jsonl`
- Review queue: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_queue.jsonl`
- Editable command file: `outputs/evaluations/hf_token_classifier_distilbert_colab_t4_span_review_commands.txt`

Workflow:

1. Open the editable command file.
2. For each record below, compare the current span arguments with the original command text and error context.
3. Edit only spans that are actually wrong after human review.
4. Rebuild with `scripts/rebuild_span_dataset_from_commands.py` when the command file has been reviewed.

## human_cmd_046

Text: `Search the open field for a missing vehicle.`

Review fields: `constraint, location, target`
Focus errors: `6`; token errors: `5`
Current gold span arguments: action='Search', location='open field', target='missing vehicle'
False negatives from model comparison: location='open field', target='missing vehicle'
False positives from model comparison: constraint='for', constraint='vehicle', target='open field', target='a', target='missing'

## human_cmd_045

Text: `Survey the stadium entrances and report areas of heavy crowding.`

Review fields: `constraint, target`
Focus errors: `6`; token errors: `4`
Current gold span arguments: action='Survey', target='stadium entrances', target='areas of heavy crowding'
False negatives from model comparison: target='stadium entrances', target='areas of heavy crowding'
False positives from model comparison: constraint='of heavy crowding', target='stadium', target='entrances', target='areas'

## human_cmd_049

Text: `Send four drones to split the industrial zone into equal sections and report anything unusual.`

Review fields: `action, constraint, target`
Focus errors: `2`; token errors: `5`
Current gold span arguments: action='Send', count='four drones', target='industrial zone', constraint='into equal sections', target='anything unusual'
False negatives from model comparison: action='Send', constraint='into equal sections'
False positives from model comparison: action='split', target='sections'

## human_cmd_047

Text: `Dispatch two drones to survey the parking lot for blocked exits.`

Review fields: `constraint, target`
Focus errors: `2`; token errors: `2`
Current gold span arguments: count='two drones', action='survey', target='parking lot', target='blocked exits'
False negatives from model comparison: target='blocked exits'
False positives from model comparison: constraint='blocked exits'

## human_cmd_044

Text: `Survey the entire farm using the fewest available drones.`

Review fields: `constraint, count`
Focus errors: `2`; token errors: `1`
Current gold span arguments: action='Survey', target='entire farm', constraint='using the fewest available drones'
False negatives from model comparison: constraint='using the fewest available drones'
False positives from model comparison: constraint='using the fewest available', count='drones'

## human_cmd_030

Text: `Send whichever drone has the most battery to the greenhouse.`

Review fields: `constraint, count`
Focus errors: `1`; token errors: `6`
Current gold span arguments: action='Send', count='whichever drone has the most battery', location='greenhouse'
False negatives from model comparison: count='whichever drone has the most battery'
False positives from model comparison: constraint='has the most battery to the', count='whichever drone'

## human_cmd_050

Text: `Send the drone with the highest battery to inspect the water tank.`

Review fields: `action, constraint, count`
Focus errors: `1`; token errors: `5`
Current gold span arguments: count='the drone with the highest battery', action='inspect', target='water tank'
False negatives from model comparison: count='the drone with the highest battery'
False positives from model comparison: action='Send', constraint='the highest battery', count='the drone', count='with'

## human_cmd_048

Text: `Inspect the railway tracks, then return to base.`

Review fields: `constraint, location`
Focus errors: `1`; token errors: `1`
Current gold span arguments: action='Inspect', target='railway tracks', location='base'
False negatives from model comparison: location='base'
False positives from model comparison: constraint='base'

## human_cmd_042

Text: `Send two drones to the canal while one drone monitors the crops.`

Review fields: `action`
Focus errors: `0`; token errors: `1`
Current gold span arguments: count='two drones', location='canal', count='one drone', action='monitors', target='crops'
False negatives from model comparison: none
False positives from model comparison: action='Send'
