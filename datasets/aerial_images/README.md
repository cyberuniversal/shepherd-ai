# Aerial Image Datasets

Store small manifests or documentation for aerial image datasets here.

Do not commit large downloaded datasets or model outputs. For VisDrone, UAVDT, DOTA, xView, Agriculture-Vision, or any other public dataset, record:

- official source URL,
- access date,
- license or access constraints,
- subset used,
- labels available,
- split definitions,
- preprocessing steps.

The expected manifest path for Week 6 is:

- `datasets/aerial_images/manifest.jsonl`

Required JSONL fields:

- `id`
- `image_path`
- `split`
- `source`
- `data_type`
- `license`
- `provenance_url`

Validate it with:

```powershell
python scripts/validate_vision_manifest.py --manifest datasets/aerial_images/manifest.jsonl --dataset-root . --summary-output outputs/evaluations/week6_vision_manifest_summary.json
```
