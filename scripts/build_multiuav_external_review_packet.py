"""Build the hash-bound external manuscript review packet and manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.multiuav_external_review import (  # noqa: E402
    build_external_review_packet,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--internal-audit",
        type=Path,
        default=(
            ROOT
            / "outputs"
            / "evaluations"
            / "multiuav_manuscript_traceability_v1.json"
        ),
    )
    parser.add_argument(
        "--packet",
        type=Path,
        default=ROOT / "reports" / "multiuav_external_review_packet_v1.md",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=(
            ROOT
            / "outputs"
            / "evaluations"
            / "multiuav_external_review_packet_v1.json"
        ),
    )
    args = parser.parse_args()

    result = build_external_review_packet(
        repository_root=args.root,
        packet_path=args.packet,
        internal_audit_path=args.internal_audit,
    )
    result["source_code_sha256"][
        "build_multiuav_external_review_packet.py"
    ] = _sha256_file(Path(__file__))
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.manifest.write_bytes(rendered.encode("utf-8"))
    print(rendered, end="")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
