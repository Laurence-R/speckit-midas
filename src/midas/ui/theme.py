"""UI theme constants and helpers."""
from __future__ import annotations

import customtkinter as ctk

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------

# Primary sans-serif family — supports Traditional Chinese on Windows
DEFAULT_FONT_FAMILY = "Microsoft JhengHei UI"

# Global font size offset applied to every make_font() call.
# Controlled by Settings page.  Values: -2 (小) | 0 (中) | +2 (大)
_font_scale: int = 0


def set_font_scale(scale: int) -> None:
    """Set the global font size offset.  Rebuilding all UI pages is required to apply."""
    global _font_scale  # noqa: PLW0603
    _font_scale = scale


def get_font_scale() -> int:
    """Return the current font size offset."""
    return _font_scale


def make_font(size: int = 13, weight: str = "normal", **kwargs) -> ctk.CTkFont:
    """Return a CTkFont using the project's default sans-serif family.

    The global font scale offset is applied automatically so that the
    Settings page font-size control affects every widget.
    """
    return ctk.CTkFont(
        family=DEFAULT_FONT_FAMILY,
        size=max(9, size + _font_scale),
        weight=weight,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Colour palettes  (modern fintech dark / light)
# ---------------------------------------------------------------------------

DARK_PALETTE: dict[str, str] = {
    # Backgrounds — layered deep navy
    "bg_primary":   "#0B1120",
    "bg_secondary": "#141E31",
    "bg_card":      "#1C2B45",
    # Accent — electric sky blue
    "accent":       "#38BDF8",
    # Subtle divider / border
    "border":       "#263552",
    # Text
    "text_primary":   "#E2EAF7",
    "text_secondary": "#7A93B4",
    # System states (non-price)
    "success": "#34D399",
    "warning": "#FBBF24",
    "error":   "#F87171",
    # Market sentiment  (台股慣例: 上漲=紅, 下跌=綠)
    "sentiment_positive": "#F87171",
    "sentiment_negative": "#34D399",
    "sentiment_neutral":  "#7A93B4",
}

LIGHT_PALETTE: dict[str, str] = {
    "bg_primary":   "#F1F5FB",
    "bg_secondary": "#FFFFFF",
    "bg_card":      "#FFFFFF",
    "accent":       "#0EA5E9",
    "border":       "#CBD5E8",
    "text_primary":   "#0D1B2E",
    "text_secondary": "#4A6585",
    "success": "#059669",
    "warning": "#D97706",
    "error":   "#DC2626",
    "sentiment_positive": "#DC2626",
    "sentiment_negative": "#059669",
    "sentiment_neutral":  "#4A6585",
}


def apply_theme(mode: str = "dark") -> None:
    """Apply CTk appearance mode ('dark' or 'light')."""
    ctk.set_appearance_mode(mode)


def get_palette(mode: str = "dark") -> dict[str, str]:
    """Return the colour palette for the given mode."""
    return DARK_PALETTE if mode == "dark" else LIGHT_PALETTE
