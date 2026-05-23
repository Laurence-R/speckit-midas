"""Validate key text/background pairs meet WCAG AA contrast ratio."""
from __future__ import annotations

from midas.ui.theme import DARK_PALETTE, LIGHT_PALETTE

NORMAL_TEXT_MIN = 4.5
LARGE_TEXT_MIN = 3.0


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def _linearize(channel: float) -> float:
    return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4


def _luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def _contrast_ratio(foreground: str, background: str) -> float:
    l1 = _luminance(foreground)
    l2 = _luminance(background)
    bright, dark = max(l1, l2), min(l1, l2)
    return (bright + 0.05) / (dark + 0.05)


def _check_palette(name: str, palette: dict[str, str]) -> list[str]:
    failures: list[str] = []
    checks = [
        ("text_primary", "bg_primary", NORMAL_TEXT_MIN, "normal"),
        ("text_primary", "bg_card", NORMAL_TEXT_MIN, "normal"),
        ("text_secondary", "bg_primary", LARGE_TEXT_MIN, "large"),
        ("text_secondary", "bg_secondary", LARGE_TEXT_MIN, "large"),
    ]

    for fg, bg, threshold, category in checks:
        ratio = _contrast_ratio(palette[fg], palette[bg])
        if ratio < threshold:
            failures.append(
                f"[{name}] {fg} on {bg} contrast {ratio:.2f} < {threshold:.1f} ({category})"
            )
    return failures


def main() -> int:
    failures = _check_palette("dark", DARK_PALETTE) + _check_palette("light", LIGHT_PALETTE)
    if failures:
        print("Contrast check FAILED")
        for line in failures:
            print(f"- {line}")
        return 1

    print("Contrast check PASSED (WCAG AA sample pairs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
