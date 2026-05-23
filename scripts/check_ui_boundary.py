"""Validate UI layer does not import provider, network, or sqlite modules directly."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = ROOT / "src" / "midas" / "ui"

FORBIDDEN = (
    r"^\s*import\s+requests\b",
    r"^\s*from\s+requests\s+import\b",
    r"^\s*import\s+sqlite3\b",
    r"^\s*from\s+sqlite3\s+import\b",
    r"^\s*from\s+midas\.integrations\b",
    r"^\s*import\s+FinMind\b",
    r"^\s*from\s+FinMind\b",
)
PATTERNS = [re.compile(p) for p in FORBIDDEN]


def main() -> int:
    violations: list[str] = []

    for file in UI_ROOT.rglob("*.py"):
        rel = file.relative_to(ROOT).as_posix()
        for line_no, line in enumerate(file.read_text(encoding="utf-8").splitlines(), start=1):
            if any(pattern.search(line) for pattern in PATTERNS):
                violations.append(f"{rel}:{line_no}: {line.strip()}")

    if violations:
        print("UI boundary check FAILED")
        for item in violations:
            print(f"- {item}")
        return 1

    print("UI boundary check PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
