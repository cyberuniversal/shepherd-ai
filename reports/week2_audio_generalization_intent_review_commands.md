# Week 2 Audio Intent Review Commands

This is a human-review aid. The exported JSONL starts from deterministic parser drafts and is not gold data.

- Draft packet: `reports\week2_audio_generalization_intent_review_packet.jsonl`
- Editable review file: `reports\week2_audio_generalization_intent_review_commands.jsonl`
- Records: `30`

Workflow:

1. Open the editable JSONL review file.
2. For each line, compare `text` against the intent fields.
3. Correct `action`, `count`, `location`, `target`, and `constraints`.
4. Change `review_status` to `human_reviewed`, `data_type` to `human_verified_audio_intent_command`, and `label_source` to `human_reviewed_v1` only after review.
5. Apply the reviewed file with `scripts/apply_audio_intent_review_commands.py`.

Draft flag counts:

- `action_missing_or_unsupported`: 4
- `constraint_review_needed`: 9
- `count_missing`: 14
- `count_not_stated`: 14
- `generic_target_area`: 4
- `location_not_stated`: 25
- `target_missing`: 6
- `target_not_stated`: 6

## audio_generalization_001_intent

Text: `Send one drone to inspect the loading bay before noon.`
Split: `validation`
Draft flags: `constraint_review_needed, location_not_stated`
Draft intent: action='inspect', count=1, location=None, target='loading bay', constraints=['before noon']

## audio_generalization_002_intent

Text: `Have two drones scan the service road for stalled vehicles.`
Split: `validation`
Draft flags: `location_not_stated`
Draft intent: action='scan', count=2, location=None, target='service road', constraints=[]

## audio_generalization_003_intent

Text: `Dispatch drone four to check the maintenance yard.`
Split: `validation`
Draft flags: `location_not_stated`
Draft intent: action='inspect', count=1, location=None, target='maintenance yard', constraints=[]

## audio_generalization_004_intent

Text: `Survey the north gate and report any blocked access points.`
Split: `validation`
Draft flags: `count_missing, count_not_stated`
Draft intent: action='inspect', count=None, location='north', target='north gate', constraints=[]

## audio_generalization_005_intent

Text: `Send the closest drone to search the storage courtyard.`
Split: `validation`
Draft flags: `constraint_review_needed, location_not_stated`
Draft intent: action='search', count=1, location=None, target='storage courtyard', constraints=['closest drone']

## audio_generalization_006_intent

Text: `Inspect the emergency exit area without flying over the crowd.`
Split: `validation`
Draft flags: `constraint_review_needed, count_missing, count_not_stated, generic_target_area, location_not_stated`
Draft intent: action='inspect', count=None, location=None, target='area', constraints=['without flying over the crowd']

## audio_generalization_007_intent

Text: `Use three drones to map the outer fence from east to west.`
Split: `validation`
Draft flags: `action_missing_or_unsupported, location_not_stated, target_missing, target_not_stated`
Draft intent: action=None, count=3, location=None, target=None, constraints=[]

## audio_generalization_008_intent

Text: `Check the lower roof for standing water after the rain.`
Split: `validation`
Draft flags: `constraint_review_needed, count_missing, count_not_stated, location_not_stated`
Draft intent: action='inspect', count=None, location=None, target='lower roof', constraints=['after the rain']

## audio_generalization_009_intent

Text: `Send all available drones back to the launch area.`
Split: `validation`
Draft flags: `generic_target_area, location_not_stated`
Draft intent: action='send', count='all', location=None, target='area', constraints=[]

## audio_generalization_010_intent

Text: `Scan the delivery lane for anything blocking the trucks.`
Split: `validation`
Draft flags: `count_missing, count_not_stated, location_not_stated`
Draft intent: action='scan', count=None, location=None, target='delivery lane', constraints=[]

## audio_generalization_011_intent

Text: `Dispatch two drones to inspect the festival entrance.`
Split: `test`
Draft flags: `location_not_stated`
Draft intent: action='inspect', count=2, location=None, target='festival entrance', constraints=[]

## audio_generalization_012_intent

Text: `Search the west courtyard for a blue maintenance cart.`
Split: `test`
Draft flags: `count_missing, count_not_stated`
Draft intent: action='search', count=None, location='west', target='blue maintenance cart', constraints=[]

## audio_generalization_013_intent

Text: `Have drone two follow the service path and take photos.`
Split: `test`
Draft flags: `action_missing_or_unsupported, location_not_stated, target_missing, target_not_stated`
Draft intent: action=None, count=1, location=None, target=None, constraints=[]

## audio_generalization_014_intent

Text: `Send one drone above the loading area but stay below sixty meters.`
Split: `test`
Draft flags: `constraint_review_needed, generic_target_area, location_not_stated`
Draft intent: action='send', count=1, location=None, target='area', constraints=['below sixty meters']

## audio_generalization_015_intent

Text: `Inspect the temporary barriers near the visitor entrance.`
Split: `test`
Draft flags: `count_missing, count_not_stated, location_not_stated`
Draft intent: action='inspect', count=None, location=None, target='temporary barriers near the visitor entrance', constraints=[]

## audio_generalization_016_intent

Text: `Survey the east service gate after the security team leaves.`
Split: `test`
Draft flags: `constraint_review_needed, count_missing, count_not_stated`
Draft intent: action='inspect', count=None, location='east', target='east service gate', constraints=['after the security team leaves']

## audio_generalization_017_intent

Text: `Send the drone with the strongest signal to inspect the far corner.`
Split: `test`
Draft flags: `location_not_stated`
Draft intent: action='inspect', count=1, location=None, target='far corner', constraints=[]

## audio_generalization_018_intent

Text: `Scan the bus drop off area for crowded sections.`
Split: `test`
Draft flags: `count_missing, count_not_stated, generic_target_area, location_not_stated`
Draft intent: action='scan', count=None, location=None, target='area', constraints=[]

## audio_generalization_019_intent

Text: `Return drone five to base after it finishes the roof check.`
Split: `test`
Draft flags: `constraint_review_needed, location_not_stated, target_missing, target_not_stated`
Draft intent: action='inspect', count=1, location=None, target=None, constraints=['after it finishes the roof check']

## audio_generalization_020_intent

Text: `Capture images of the broken gate and send a report.`
Split: `test`
Draft flags: `count_missing, count_not_stated, location_not_stated`
Draft intent: action='capture', count=None, location=None, target='broken gate and send a report', constraints=[]

## audio_generalization_021_intent

Text: `Use two drones to inspect the shaded walkway and the side entrance.`
Split: `test`
Draft flags: `location_not_stated`
Draft intent: action='inspect', count=2, location=None, target='shaded walkway and the side entrance', constraints=[]

## audio_generalization_022_intent

Text: `Search the empty lot behind the clinic for parked vans.`
Split: `test`
Draft flags: `count_missing, count_not_stated, location_not_stated`
Draft intent: action='search', count=None, location=None, target='parked vans', constraints=[]

## audio_generalization_023_intent

Text: `Send drone six north of the service building and hold position.`
Split: `test`
Draft flags: `target_missing, target_not_stated`
Draft intent: action='hold', count=1, location='north', target=None, constraints=[]

## audio_generalization_024_intent

Text: `Inspect the drainage channel and look for overflow.`
Split: `test`
Draft flags: `count_missing, count_not_stated, location_not_stated`
Draft intent: action='inspect', count=None, location=None, target='drainage channel and look', constraints=[]

## audio_generalization_025_intent

Text: `Survey the market street without crossing the restricted line.`
Split: `test`
Draft flags: `constraint_review_needed, count_missing, count_not_stated, location_not_stated`
Draft intent: action='inspect', count=None, location=None, target='market street', constraints=['without crossing the restricted line']

## audio_generalization_026_intent

Text: `Send three drones to divide the campus into separate search areas.`
Split: `test`
Draft flags: `location_not_stated`
Draft intent: action='search', count=3, location=None, target='areas', constraints=[]

## audio_generalization_027_intent

Text: `Check the prayer hall entrance for blocked doors.`
Split: `test`
Draft flags: `count_missing, count_not_stated, location_not_stated`
Draft intent: action='inspect', count=None, location=None, target='prayer hall entrance', constraints=[]

## audio_generalization_028_intent

Text: `Have the nearest drone photograph the damaged sign.`
Split: `test`
Draft flags: `action_missing_or_unsupported, constraint_review_needed, location_not_stated, target_missing, target_not_stated`
Draft intent: action=None, count=1, location=None, target=None, constraints=['nearest drone']

## audio_generalization_029_intent

Text: `Monitor the main road until the ambulance arrives.`
Split: `test`
Draft flags: `action_missing_or_unsupported, count_missing, count_not_stated, location_not_stated, target_missing, target_not_stated`
Draft intent: action=None, count=None, location=None, target=None, constraints=[]

## audio_generalization_030_intent

Text: `Send one drone to the southern wall, then return it to the launch area.`
Split: `test`
Draft flags: `none`
Draft intent: action='return', count=1, location='south', target='drones', constraints=[]
