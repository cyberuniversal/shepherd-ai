# Week 2 Audio Intent Review Packet

Draft intent-label review packet only. Labels come from the deterministic parser and must be human-reviewed before training, evaluation, or accuracy claims.

## Summary

- Records: 30
- Split counts: `{"test": 20, "validation": 10}`
- Draft label source: `deterministic_v1_draft`
- Draft review flag counts: `{"action_missing_or_unsupported": 4, "constraint_review_needed": 9, "count_missing": 14, "count_not_stated": 14, "generic_target_area": 4, "location_not_stated": 25, "target_missing": 6, "target_not_stated": 6}`

## Review Instructions

- Listen to the WAV file if there is any transcript doubt.
- Correct `action`, `count`, `location`, `target`, and `constraints` in the JSONL packet.
- Keep `review_status` as `needs_human_review` until a human has checked the record.
- After review, change `review_status` to `human_reviewed` and set `data_type` to `human_verified_audio_intent_command`.
- Do not use draft records for training or accuracy reporting.

## Draft Records

| ID | Split | Transcript | Draft flags | Draft intent |
| --- | --- | --- | --- | --- |
| `audio_generalization_001_intent` | `validation` | Send one drone to inspect the loading bay before noon. | `constraint_review_needed, location_not_stated` | `{"action": "inspect", "constraints": ["before noon"], "count": 1, "location": null, "target": "loading bay"}` |
| `audio_generalization_002_intent` | `validation` | Have two drones scan the service road for stalled vehicles. | `location_not_stated` | `{"action": "scan", "constraints": [], "count": 2, "location": null, "target": "service road"}` |
| `audio_generalization_003_intent` | `validation` | Dispatch drone four to check the maintenance yard. | `location_not_stated` | `{"action": "inspect", "constraints": [], "count": 1, "location": null, "target": "maintenance yard"}` |
| `audio_generalization_004_intent` | `validation` | Survey the north gate and report any blocked access points. | `count_missing, count_not_stated` | `{"action": "inspect", "constraints": [], "count": null, "location": "north", "target": "north gate"}` |
| `audio_generalization_005_intent` | `validation` | Send the closest drone to search the storage courtyard. | `constraint_review_needed, location_not_stated` | `{"action": "search", "constraints": ["closest drone"], "count": 1, "location": null, "target": "storage courtyard"}` |
| `audio_generalization_006_intent` | `validation` | Inspect the emergency exit area without flying over the crowd. | `constraint_review_needed, count_missing, count_not_stated, generic_target_area, location_not_stated` | `{"action": "inspect", "constraints": ["without flying over the crowd"], "count": null, "location": null, "target": "area"}` |
| `audio_generalization_007_intent` | `validation` | Use three drones to map the outer fence from east to west. | `action_missing_or_unsupported, location_not_stated, target_missing, target_not_stated` | `{"action": null, "constraints": [], "count": 3, "location": null, "target": null}` |
| `audio_generalization_008_intent` | `validation` | Check the lower roof for standing water after the rain. | `constraint_review_needed, count_missing, count_not_stated, location_not_stated` | `{"action": "inspect", "constraints": ["after the rain"], "count": null, "location": null, "target": "lower roof"}` |
| `audio_generalization_009_intent` | `validation` | Send all available drones back to the launch area. | `generic_target_area, location_not_stated` | `{"action": "send", "constraints": [], "count": "all", "location": null, "target": "area"}` |
| `audio_generalization_010_intent` | `validation` | Scan the delivery lane for anything blocking the trucks. | `count_missing, count_not_stated, location_not_stated` | `{"action": "scan", "constraints": [], "count": null, "location": null, "target": "delivery lane"}` |
| `audio_generalization_011_intent` | `test` | Dispatch two drones to inspect the festival entrance. | `location_not_stated` | `{"action": "inspect", "constraints": [], "count": 2, "location": null, "target": "festival entrance"}` |
| `audio_generalization_012_intent` | `test` | Search the west courtyard for a blue maintenance cart. | `count_missing, count_not_stated` | `{"action": "search", "constraints": [], "count": null, "location": "west", "target": "blue maintenance cart"}` |
| `audio_generalization_013_intent` | `test` | Have drone two follow the service path and take photos. | `action_missing_or_unsupported, location_not_stated, target_missing, target_not_stated` | `{"action": null, "constraints": [], "count": 1, "location": null, "target": null}` |
| `audio_generalization_014_intent` | `test` | Send one drone above the loading area but stay below sixty meters. | `constraint_review_needed, generic_target_area, location_not_stated` | `{"action": "send", "constraints": ["below sixty meters"], "count": 1, "location": null, "target": "area"}` |
| `audio_generalization_015_intent` | `test` | Inspect the temporary barriers near the visitor entrance. | `count_missing, count_not_stated, location_not_stated` | `{"action": "inspect", "constraints": [], "count": null, "location": null, "target": "temporary barriers near the visitor entrance"}` |
| `audio_generalization_016_intent` | `test` | Survey the east service gate after the security team leaves. | `constraint_review_needed, count_missing, count_not_stated` | `{"action": "inspect", "constraints": ["after the security team leaves"], "count": null, "location": "east", "target": "east service gate"}` |
| `audio_generalization_017_intent` | `test` | Send the drone with the strongest signal to inspect the far corner. | `location_not_stated` | `{"action": "inspect", "constraints": [], "count": 1, "location": null, "target": "far corner"}` |
| `audio_generalization_018_intent` | `test` | Scan the bus drop off area for crowded sections. | `count_missing, count_not_stated, generic_target_area, location_not_stated` | `{"action": "scan", "constraints": [], "count": null, "location": null, "target": "area"}` |
| `audio_generalization_019_intent` | `test` | Return drone five to base after it finishes the roof check. | `constraint_review_needed, location_not_stated, target_missing, target_not_stated` | `{"action": "inspect", "constraints": ["after it finishes the roof check"], "count": 1, "location": null, "target": null}` |
| `audio_generalization_020_intent` | `test` | Capture images of the broken gate and send a report. | `count_missing, count_not_stated, location_not_stated` | `{"action": "capture", "constraints": [], "count": null, "location": null, "target": "broken gate and send a report"}` |
| `audio_generalization_021_intent` | `test` | Use two drones to inspect the shaded walkway and the side entrance. | `location_not_stated` | `{"action": "inspect", "constraints": [], "count": 2, "location": null, "target": "shaded walkway and the side entrance"}` |
| `audio_generalization_022_intent` | `test` | Search the empty lot behind the clinic for parked vans. | `count_missing, count_not_stated, location_not_stated` | `{"action": "search", "constraints": [], "count": null, "location": null, "target": "parked vans"}` |
| `audio_generalization_023_intent` | `test` | Send drone six north of the service building and hold position. | `target_missing, target_not_stated` | `{"action": "hold", "constraints": [], "count": 1, "location": "north", "target": null}` |
| `audio_generalization_024_intent` | `test` | Inspect the drainage channel and look for overflow. | `count_missing, count_not_stated, location_not_stated` | `{"action": "inspect", "constraints": [], "count": null, "location": null, "target": "drainage channel and look"}` |
| `audio_generalization_025_intent` | `test` | Survey the market street without crossing the restricted line. | `constraint_review_needed, count_missing, count_not_stated, location_not_stated` | `{"action": "inspect", "constraints": ["without crossing the restricted line"], "count": null, "location": null, "target": "market street"}` |
| `audio_generalization_026_intent` | `test` | Send three drones to divide the campus into separate search areas. | `location_not_stated` | `{"action": "search", "constraints": [], "count": 3, "location": null, "target": "areas"}` |
| `audio_generalization_027_intent` | `test` | Check the prayer hall entrance for blocked doors. | `count_missing, count_not_stated, location_not_stated` | `{"action": "inspect", "constraints": [], "count": null, "location": null, "target": "prayer hall entrance"}` |
| `audio_generalization_028_intent` | `test` | Have the nearest drone photograph the damaged sign. | `action_missing_or_unsupported, constraint_review_needed, location_not_stated, target_missing, target_not_stated` | `{"action": null, "constraints": ["nearest drone"], "count": 1, "location": null, "target": null}` |
| `audio_generalization_029_intent` | `test` | Monitor the main road until the ambulance arrives. | `action_missing_or_unsupported, count_missing, count_not_stated, location_not_stated, target_missing, target_not_stated` | `{"action": null, "constraints": [], "count": null, "location": null, "target": null}` |
| `audio_generalization_030_intent` | `test` | Send one drone to the southern wall, then return it to the launch area. | `none` | `{"action": "return", "constraints": [], "count": 1, "location": "south", "target": "drones"}` |
