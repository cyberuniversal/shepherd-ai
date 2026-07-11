"""Rebuild the span-labeled command dataset from saved label commands.

Only commands that invoke scripts/create_span_record_from_command.py are
accepted. This avoids executing arbitrary shell content from a notes file.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CREATE_SCRIPT = ROOT / "scripts" / "create_span_record_from_command.py"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_span_dataset.py"
ALLOWED_SCRIPT_NAMES = {
    "scripts/create_span_record_from_command.py",
    "scripts\\create_span_record_from_command.py",
    "create_span_record_from_command.py",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commands-file", required=True, help="Text file containing one label command per line.")
    parser.add_argument("--output", default="datasets/commands/human_verified_span_commands.jsonl")
    parser.add_argument("--summary-output", default="outputs/evaluations/human_verified_span_commands_summary.json")
    parser.add_argument("--bio-output", default="outputs/evaluations/human_verified_span_commands_bio.jsonl")
    parser.add_argument("--no-backup", action="store_true", help="Do not back up an existing output file.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    commands = _load_commands(Path(args.commands_file))
    if not commands:
        raise ValueError("commands file contains no label commands")

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output.with_name(f"{output.name}.tmp-rebuild")
    if temp_output.exists():
        temp_output.unlink()

    for line_number, raw_line in commands:
        command_args = _create_script_args(raw_line, line_number=line_number, forced_output=temp_output)
        subprocess.run([sys.executable, str(CREATE_SCRIPT), *command_args], cwd=ROOT, check=True)

    _run_validation(temp_output, Path(args.summary_output), Path(args.bio_output))

    backup_path: Path | None = None
    if output.exists() and not args.no_backup:
        backup_path = _backup_path(output)
        shutil.copy2(output, backup_path)
    shutil.move(str(temp_output), output)

    summary = json.loads(Path(args.summary_output).read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "commands": len(commands),
                "output": str(output),
                "backup": str(backup_path) if backup_path else None,
                "records": summary["records"],
                "span_field_counts": summary["span_field_counts"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_commands(path: Path) -> list[tuple[int, str]]:
    commands: list[tuple[int, str]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = _strip_prompt(raw_line.strip())
        if not line or line.startswith("#"):
            continue
        if _is_legacy_cleanup_line(line):
            continue
        commands.append((line_number, line))
    return commands


def _strip_prompt(line: str) -> str:
    marker = "python "
    lower_line = line.lower()
    index = lower_line.find(marker)
    if index > 0:
        return line[index:]
    return line


def _is_legacy_cleanup_line(line: str) -> bool:
    return (
        line.startswith("python -c ")
        and "human_verified_span_commands.jsonl" in line
        and "unlink(missing_ok=True)" in line
    )


def _create_script_args(raw_line: str, *, line_number: int, forced_output: Path) -> list[str]:
    parts = shlex.split(raw_line)
    if len(parts) < 2:
        raise ValueError(f"line {line_number}: unsupported command")
    executable = Path(parts[0]).name.lower()
    if executable not in {"python", "python.exe", "py", "py.exe"}:
        raise ValueError(f"line {line_number}: unsupported command")
    script = parts[1].replace("/", "\\")
    if script not in {name.replace("/", "\\") for name in ALLOWED_SCRIPT_NAMES}:
        raise ValueError(f"line {line_number}: unsupported command")
    args = parts[2:]
    args = _replace_or_append_option(args, "--output", str(forced_output))
    return args


def _replace_or_append_option(args: list[str], option: str, value: str) -> list[str]:
    updated = list(args)
    if option in updated:
        index = updated.index(option)
        if index == len(updated) - 1:
            raise ValueError(f"{option} requires a value")
        updated[index + 1] = value
        return updated
    updated.extend([option, value])
    return updated


def _run_validation(dataset: Path, summary_output: Path, bio_output: Path) -> None:
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    bio_output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            str(VALIDATE_SCRIPT),
            "--dataset",
            str(dataset),
            "--summary-output",
            str(summary_output),
            "--bio-output",
            str(bio_output),
        ],
        cwd=ROOT,
        check=True,
    )


def _backup_path(output: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return output.with_name(f"{output.name}.bak-{stamp}")


if __name__ == "__main__":
    main()
