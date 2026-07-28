# MultiUAV-Plat Source Acquisition And Audit

## Purpose

This procedure pins and verifies the benchmark source for the proposed
MultiUAV-Plat validation-placement study. It does not generate Shepherd-AI
cases, expose hidden reference data to a model, or produce evaluation results.

## Pinned Source

- Repository: `https://github.com/zhangsheng93/MultiUAV-Plat`
- Commit: `1794e45e421fb5de03094f0b63f9ca95f86ab42f`
- Commit date: 2026-07-21T22:15:31+08:00
- Benchmark archive: `benchmark/benchmark.zip`
- Archive size: 11,709,646 bytes
- Archive SHA-256:
  `b5040097d2bfdd44600f3bf486fdb43ee3eb1247fec9c67900b5fcda6feb94a3`
- License: GPL-3.0, as identified by the upstream repository license file
- License SHA-256:
  `230184f60bae2feaf244f10a8bac053c8ff33a183bcc365b4d8b876d2b7f4809`

## Reproducible Acquisition

Run from the Shepherd-AI repository root:

```powershell
git clone --filter=blob:none --no-checkout `
  https://github.com/zhangsheng93/MultiUAV-Plat.git `
  external/MultiUAV-Plat
git -C external/MultiUAV-Plat checkout `
  1794e45e421fb5de03094f0b63f9ca95f86ab42f
python scripts/audit_multiuav_plat_source.py `
  --repository-root external/MultiUAV-Plat `
  --output outputs/multiuav/source_audit.json
```

The checkout is intentionally ignored by Shepherd-AI Git. The committed source
registry is `datasets/multiuav_plat/source_registry_v1.json`.

## Reproduced Source Facts

The local archive audit reproduced:

- 75 session JSON files paired with 75 JPG files;
- 1,500 globally unique task IDs;
- 9,396 leaf validation checks, counted recursively;
- 5,794 upstream `content_aliases`;
- 1,443 unique normalized canonical instructions out of 1,500; and
- three scenario families with 25 sessions each.

The 75 sessions contain 15 sessions for each filename-level difficulty:
`easy`, `intermediate`, `moderate`, `hard`, and `extreme`.

## Leakage Boundary

The upstream task object colocates public instruction text with privileged
reference information. Shepherd-AI dataset construction must use the positive
allowlist `id`, `content`, and `content_aliases`. It must not copy these task
fields into model inputs:

- `related_apis`;
- `execution_check_apis`;
- `commands`;
- `is_done`; or
- `is_passed`.

Session `history` and `statistics` are also privileged. Mission context for an
evaluated model must be obtained through the official AGENT-role interface or
through a separately specified, tested projection that reproduces that
interface's masking behavior. Raw session JSON is not model-visible context.

The upstream server explicitly masks `related_apis`, `commands`, and
`execution_check_apis` for AGENT and USER roles. Shepherd-AI applies the more
conservative boundary above because outcome flags and history could also leak
the answer.

## Research Interpretation

This audit establishes source provenance and schema only. It does not establish
that all 1,500 tasks are usable for the proposed five-variant design. It does
not validate intervention labels, split independence, model performance,
mission completion, or any paper claim.

The 57 normalized duplicate canonical instructions mean that a session-level
split alone is insufficient as a leakage argument. The registered split must
measure exact and normalized instruction overlap and either group duplicates or
report and justify any retained overlap before model evaluation.
