"""Run the typed-command intent baseline on a roadmap example."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.intent import parse_intent  # noqa: E402


def main() -> None:
    command = "Send two drones north and inspect the crops."
    print(parse_intent(command).to_json())


if __name__ == "__main__":
    main()
