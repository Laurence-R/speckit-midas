"""Heuristic spacing token checker for UI pages/components."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = ROOT / "src" / "midas" / "ui"
ALLOWED_LITERALS = {0, 1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24, 40}
PATTERN = re.compile(r"\b(padx|pady)\s*=\s*(\d+)")


def main() -> int:
    violations: list[str] = []
    checked = 0

    for file in UI_ROOT.rglob("*.py"):
        text = file.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for _, value in PATTERN.findall(line):
                checked += 1
                number = int(value)
                if number not in ALLOWED_LITERALS:
                    rel = file.relative_to(ROOT).as_posix()
                    violations.append(f"{rel}:{line_no} unexpected spacing literal {number}")

    print(f"Checked spacing declarations: {checked}")
    if violations:
        print("Spacing token check FAILED")
        for item in violations:
            print(f"- {item}")
        return 1

    print("Spacing token check PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
