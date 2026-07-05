# Week 2 Audio Intent Review Packet

Draft intent-label review packet only. Labels come from the deterministic parser and must be human-reviewed before training, evaluation, or accuracy claims.

## Summary

- Records: 30
- Split counts: `{"test": 20, "validation": 10}`
- Draft label source: `deterministic_v2_draft`
- Draft review flag counts: `{"constraint_review_needed": 9, "count_missing": 18, "count_not_stated": 18, "location_not_stated": 15, "target_missing": 4, "target_not_stated": 3}`

## Review Instructions

- Listen to the WAV file if there is any transcript doubt.
- Correct `action`, `count`, `location`, `target`, and `constraints` in the JSONL packet.
- Keep `review_status` as `needs_human_review` until a human has checked the record.
- After review, change `review_status` to `human_reviewed` and set `data_type` to `human_verified_audio_intent_command`.
- Do not use draft records for training or accuracy reporting.

## Draft Records

| ID | Split | Transcript | Draft flags | Draft intent |
| --- | --- | --- | --- | --- |
| `audio_v2_holdout_001_intent` | `validation` | Inspect the generator shed for smoke before sunset. | `constraint_review_needed, count_missing, count_not_stated` | `{"action": "inspect", "constraints": ["before sunset"], "count": null, "location": "generator shed", "target": "smoke"}` |
| `audio_v2_holdout_002_intent` | `validation` | Send two drones to scan the hotel driveway for stopped cars. | `none` | `{"action": "scan", "constraints": [], "count": 2, "location": "hotel driveway", "target": "stopped cars"}` |
| `audio_v2_holdout_003_intent` | `validation` | Have drone three photograph the cracked pavement near the gatehouse. | `location_not_stated` | `{"action": "capture", "constraints": [], "count": 1, "location": null, "target": "cracked pavement near the gatehouse"}` |
| `audio_v2_holdout_004_intent` | `validation` | Search the picnic area for a lost backpack. | `count_missing, count_not_stated` | `{"action": "search", "constraints": [], "count": null, "location": "picnic area", "target": "lost backpack"}` |
| `audio_v2_holdout_005_intent` | `validation` | Map the eastern walking path using one drone. | `constraint_review_needed` | `{"action": "scan", "constraints": ["using one drone"], "count": 1, "location": "east", "target": "eastern walking path"}` |
| `audio_v2_holdout_006_intent` | `validation` | Return the closest drone to the control tent. | `constraint_review_needed` | `{"action": "return", "constraints": ["closest drone"], "count": 1, "location": null, "target": "drones"}` |
| `audio_v2_holdout_007_intent` | `validation` | Monitor the courtyard entrance until the crowd clears. | `constraint_review_needed, count_missing, count_not_stated` | `{"action": "scan", "constraints": ["until the crowd clears"], "count": null, "location": "courtyard entrance", "target": "courtyard entrance"}` |
| `audio_v2_holdout_008_intent` | `validation` | Capture images of the damaged light pole. | `count_missing, count_not_stated, location_not_stated` | `{"action": "capture", "constraints": [], "count": null, "location": null, "target": "damaged light pole"}` |
| `audio_v2_holdout_009_intent` | `validation` | Scan the service garage without entering the marked zone. | `constraint_review_needed, count_missing, count_not_stated, location_not_stated` | `{"action": "scan", "constraints": ["without entering the marked zone"], "count": null, "location": null, "target": "service garage"}` |
| `audio_v2_holdout_010_intent` | `validation` | Send all drones to hold position above the command post. | `location_not_stated, target_missing, target_not_stated` | `{"action": "hold", "constraints": [], "count": "all", "location": null, "target": null}` |
| `audio_v2_holdout_011_intent` | `test` | Inspect the bicycle racks for abandoned items. | `count_missing, count_not_stated` | `{"action": "inspect", "constraints": [], "count": null, "location": "bicycle racks", "target": "abandoned items"}` |
| `audio_v2_holdout_012_intent` | `test` | Dispatch one drone to check the northern staircase. | `none` | `{"action": "inspect", "constraints": [], "count": 1, "location": "north", "target": "northern staircase"}` |
| `audio_v2_holdout_013_intent` | `test` | Search the gravel path behind the library for a red suitcase. | `count_missing, count_not_stated` | `{"action": "search", "constraints": [], "count": null, "location": "gravel path behind the library", "target": "red suitcase"}` |
| `audio_v2_holdout_014_intent` | `test` | Survey the hotel entrance after the buses leave. | `constraint_review_needed, count_missing, count_not_stated, location_not_stated` | `{"action": "inspect", "constraints": ["after the buses leave"], "count": null, "location": null, "target": "hotel entrance"}` |
| `audio_v2_holdout_015_intent` | `test` | Send drone eight to monitor the backup generator. | `location_not_stated` | `{"action": "scan", "constraints": [], "count": 1, "location": null, "target": "backup generator"}` |
| `audio_v2_holdout_016_intent` | `test` | Scan the food court roof for loose materials. | `count_missing, count_not_stated` | `{"action": "scan", "constraints": [], "count": null, "location": "food court roof", "target": "loose materials"}` |
| `audio_v2_holdout_017_intent` | `test` | Use two drones to inspect the visitor bridge from both ends. | `location_not_stated` | `{"action": "inspect", "constraints": [], "count": 2, "location": null, "target": "visitor bridge"}` |
| `audio_v2_holdout_018_intent` | `test` | Check the fountain area for water overflow. | `count_missing, count_not_stated` | `{"action": "inspect", "constraints": [], "count": null, "location": "fountain area", "target": "water overflow"}` |
| `audio_v2_holdout_019_intent` | `test` | Photograph the damaged railing near the upper walkway. | `count_missing, count_not_stated, location_not_stated` | `{"action": "capture", "constraints": [], "count": null, "location": null, "target": "damaged railing near the upper walkway"}` |
| `audio_v2_holdout_020_intent` | `test` | Send the drone with the clearest camera feed to inspect the control booth. | `location_not_stated` | `{"action": "inspect", "constraints": [], "count": 1, "location": null, "target": "control booth"}` |
| `audio_v2_holdout_021_intent` | `test` | Search the palm garden for signs of fire. | `count_missing, count_not_stated` | `{"action": "search", "constraints": [], "count": null, "location": "palm garden", "target": "signs of fire"}` |
| `audio_v2_holdout_022_intent` | `test` | Monitor the taxi lane while keeping away from the terminal doors. | `constraint_review_needed, count_missing, count_not_stated, location_not_stated` | `{"action": "scan", "constraints": ["while keeping away from the terminal doors"], "count": null, "location": null, "target": "taxi lane"}` |
| `audio_v2_holdout_023_intent` | `test` | Map the storage alley and report any blocked passage. | `count_missing, count_not_stated, location_not_stated` | `{"action": "scan", "constraints": [], "count": null, "location": null, "target": "storage alley"}` |
| `audio_v2_holdout_024_intent` | `test` | Return drone two after it completes the fence check. | `constraint_review_needed, location_not_stated, target_missing, target_not_stated` | `{"action": "inspect", "constraints": ["after it completes the fence check"], "count": 1, "location": null, "target": null}` |
| `audio_v2_holdout_025_intent` | `test` | Inspect the temporary stage for broken supports. | `count_missing, count_not_stated` | `{"action": "inspect", "constraints": [], "count": null, "location": "temporary stage", "target": "broken supports"}` |
| `audio_v2_holdout_026_intent` | `test` | Send three drones to cover the north, center, and south sections. | `target_missing` | `{"action": "send", "constraints": [], "count": 3, "location": "cover the north center and south sections", "target": null}` |
| `audio_v2_holdout_027_intent` | `test` | Scan the clinic entrance for people waiting outside. | `count_missing, count_not_stated` | `{"action": "scan", "constraints": [], "count": null, "location": "clinic entrance", "target": "people waiting outside"}` |
| `audio_v2_holdout_028_intent` | `test` | Hold drone four above the roundabout until further notice. | `constraint_review_needed, location_not_stated, target_missing, target_not_stated` | `{"action": "hold", "constraints": ["until further notice"], "count": 1, "location": null, "target": null}` |
| `audio_v2_holdout_029_intent` | `test` | Capture a wide photo of the overflow parking area. | `count_missing, count_not_stated, location_not_stated` | `{"action": "capture", "constraints": [], "count": null, "location": null, "target": "wide photo of the overflow parking area"}` |
| `audio_v2_holdout_030_intent` | `test` | Survey the outdoor seating area and return to the control tent. | `count_missing, count_not_stated, location_not_stated` | `{"action": "inspect", "constraints": [], "count": null, "location": null, "target": "outdoor seating area"}` |
