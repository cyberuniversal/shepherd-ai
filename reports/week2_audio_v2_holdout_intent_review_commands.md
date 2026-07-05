# Week 2 Audio Intent Review Commands

This is a human-review aid. The exported JSONL starts from deterministic parser drafts and is not gold data.

- Draft packet: `reports\week2_audio_v2_holdout_intent_review_packet.jsonl`
- Editable review file: `reports\week2_audio_v2_holdout_intent_review_commands.jsonl`
- Records: `30`

Workflow:

1. Open the editable JSONL review file.
2. For each line, compare `text` against the intent fields.
3. Correct `action`, `count`, `location`, `target`, and `constraints`.
4. Change `review_status` to `human_reviewed`, `data_type` to `human_verified_audio_intent_command`, and `label_source` to `human_reviewed_v1` only after review.
5. Apply the reviewed file with `scripts/apply_audio_intent_review_commands.py`.

Draft flag counts:

- `constraint_review_needed`: 9
- `count_missing`: 18
- `count_not_stated`: 18
- `location_not_stated`: 15
- `target_missing`: 4
- `target_not_stated`: 3

## audio_v2_holdout_001_intent

Text: `Inspect the generator shed for smoke before sunset.`
Split: `validation`
Draft flags: `constraint_review_needed, count_missing, count_not_stated`
Draft intent: action='inspect', count=None, location='generator shed', target='smoke', constraints=['before sunset']

## audio_v2_holdout_002_intent

Text: `Send two drones to scan the hotel driveway for stopped cars.`
Split: `validation`
Draft flags: `none`
Draft intent: action='scan', count=2, location='hotel driveway', target='stopped cars', constraints=[]

## audio_v2_holdout_003_intent

Text: `Have drone three photograph the cracked pavement near the gatehouse.`
Split: `validation`
Draft flags: `location_not_stated`
Draft intent: action='capture', count=1, location=None, target='cracked pavement near the gatehouse', constraints=[]

## audio_v2_holdout_004_intent

Text: `Search the picnic area for a lost backpack.`
Split: `validation`
Draft flags: `count_missing, count_not_stated`
Draft intent: action='search', count=None, location='picnic area', target='lost backpack', constraints=[]

## audio_v2_holdout_005_intent

Text: `Map the eastern walking path using one drone.`
Split: `validation`
Draft flags: `constraint_review_needed`
Draft intent: action='scan', count=1, location='east', target='eastern walking path', constraints=['using one drone']

## audio_v2_holdout_006_intent

Text: `Return the closest drone to the control tent.`
Split: `validation`
Draft flags: `constraint_review_needed`
Draft intent: action='return', count=1, location=None, target='drones', constraints=['closest drone']

## audio_v2_holdout_007_intent

Text: `Monitor the courtyard entrance until the crowd clears.`
Split: `validation`
Draft flags: `constraint_review_needed, count_missing, count_not_stated`
Draft intent: action='scan', count=None, location='courtyard entrance', target='courtyard entrance', constraints=['until the crowd clears']

## audio_v2_holdout_008_intent

Text: `Capture images of the damaged light pole.`
Split: `validation`
Draft flags: `count_missing, count_not_stated, location_not_stated`
Draft intent: action='capture', count=None, location=None, target='damaged light pole', constraints=[]

## audio_v2_holdout_009_intent

Text: `Scan the service garage without entering the marked zone.`
Split: `validation`
Draft flags: `constraint_review_needed, count_missing, count_not_stated, location_not_stated`
Draft intent: action='scan', count=None, location=None, target='service garage', constraints=['without entering the marked zone']

## audio_v2_holdout_010_intent

Text: `Send all drones to hold position above the command post.`
Split: `validation`
Draft flags: `location_not_stated, target_missing, target_not_stated`
Draft intent: action='hold', count='all', location=None, target=None, constraints=[]

## audio_v2_holdout_011_intent

Text: `Inspect the bicycle racks for abandoned items.`
Split: `test`
Draft flags: `count_missing, count_not_stated`
Draft intent: action='inspect', count=None, location='bicycle racks', target='abandoned items', constraints=[]

## audio_v2_holdout_012_intent

Text: `Dispatch one drone to check the northern staircase.`
Split: `test`
Draft flags: `none`
Draft intent: action='inspect', count=1, location='north', target='northern staircase', constraints=[]

## audio_v2_holdout_013_intent

Text: `Search the gravel path behind the library for a red suitcase.`
Split: `test`
Draft flags: `count_missing, count_not_stated`
Draft intent: action='search', count=None, location='gravel path behind the library', target='red suitcase', constraints=[]

## audio_v2_holdout_014_intent

Text: `Survey the hotel entrance after the buses leave.`
Split: `test`
Draft flags: `constraint_review_needed, count_missing, count_not_stated, location_not_stated`
Draft intent: action='inspect', count=None, location=None, target='hotel entrance', constraints=['after the buses leave']

## audio_v2_holdout_015_intent

Text: `Send drone eight to monitor the backup generator.`
Split: `test`
Draft flags: `location_not_stated`
Draft intent: action='scan', count=1, location=None, target='backup generator', constraints=[]

## audio_v2_holdout_016_intent

Text: `Scan the food court roof for loose materials.`
Split: `test`
Draft flags: `count_missing, count_not_stated`
Draft intent: action='scan', count=None, location='food court roof', target='loose materials', constraints=[]

## audio_v2_holdout_017_intent

Text: `Use two drones to inspect the visitor bridge from both ends.`
Split: `test`
Draft flags: `location_not_stated`
Draft intent: action='inspect', count=2, location=None, target='visitor bridge', constraints=[]

## audio_v2_holdout_018_intent

Text: `Check the fountain area for water overflow.`
Split: `test`
Draft flags: `count_missing, count_not_stated`
Draft intent: action='inspect', count=None, location='fountain area', target='water overflow', constraints=[]

## audio_v2_holdout_019_intent

Text: `Photograph the damaged railing near the upper walkway.`
Split: `test`
Draft flags: `count_missing, count_not_stated, location_not_stated`
Draft intent: action='capture', count=None, location=None, target='damaged railing near the upper walkway', constraints=[]

## audio_v2_holdout_020_intent

Text: `Send the drone with the clearest camera feed to inspect the control booth.`
Split: `test`
Draft flags: `location_not_stated`
Draft intent: action='inspect', count=1, location=None, target='control booth', constraints=[]

## audio_v2_holdout_021_intent

Text: `Search the palm garden for signs of fire.`
Split: `test`
Draft flags: `count_missing, count_not_stated`
Draft intent: action='search', count=None, location='palm garden', target='signs of fire', constraints=[]

## audio_v2_holdout_022_intent

Text: `Monitor the taxi lane while keeping away from the terminal doors.`
Split: `test`
Draft flags: `constraint_review_needed, count_missing, count_not_stated, location_not_stated`
Draft intent: action='scan', count=None, location=None, target='taxi lane', constraints=['while keeping away from the terminal doors']

## audio_v2_holdout_023_intent

Text: `Map the storage alley and report any blocked passage.`
Split: `test`
Draft flags: `count_missing, count_not_stated, location_not_stated`
Draft intent: action='scan', count=None, location=None, target='storage alley', constraints=[]

## audio_v2_holdout_024_intent

Text: `Return drone two after it completes the fence check.`
Split: `test`
Draft flags: `constraint_review_needed, location_not_stated, target_missing, target_not_stated`
Draft intent: action='inspect', count=1, location=None, target=None, constraints=['after it completes the fence check']

## audio_v2_holdout_025_intent

Text: `Inspect the temporary stage for broken supports.`
Split: `test`
Draft flags: `count_missing, count_not_stated`
Draft intent: action='inspect', count=None, location='temporary stage', target='broken supports', constraints=[]

## audio_v2_holdout_026_intent

Text: `Send three drones to cover the north, center, and south sections.`
Split: `test`
Draft flags: `target_missing`
Draft intent: action='send', count=3, location='cover the north center and south sections', target=None, constraints=[]

## audio_v2_holdout_027_intent

Text: `Scan the clinic entrance for people waiting outside.`
Split: `test`
Draft flags: `count_missing, count_not_stated`
Draft intent: action='scan', count=None, location='clinic entrance', target='people waiting outside', constraints=[]

## audio_v2_holdout_028_intent

Text: `Hold drone four above the roundabout until further notice.`
Split: `test`
Draft flags: `constraint_review_needed, location_not_stated, target_missing, target_not_stated`
Draft intent: action='hold', count=1, location=None, target=None, constraints=['until further notice']

## audio_v2_holdout_029_intent

Text: `Capture a wide photo of the overflow parking area.`
Split: `test`
Draft flags: `count_missing, count_not_stated, location_not_stated`
Draft intent: action='capture', count=None, location=None, target='wide photo of the overflow parking area', constraints=[]

## audio_v2_holdout_030_intent

Text: `Survey the outdoor seating area and return to the control tent.`
Split: `test`
Draft flags: `count_missing, count_not_stated, location_not_stated`
Draft intent: action='inspect', count=None, location=None, target='outdoor seating area', constraints=[]
