# Local Gazetteer

`riyadh_seed.jsonl` is a small committed seed index for offline target-resolution tests. It is not a comprehensive public map dataset and it is not parser training data.

Runtime target resolution should use a local, auditable gazetteer or map index. Unknown place names should stay unresolved until a deterministic resolver or human operator resolves them; Shepherd-AI should not invent coordinates.

Future larger indexes can be generated from approved sources such as OpenStreetMap extracts or internal operational maps, then stored under ignored local paths such as `.tmp_gazetteer/`.
