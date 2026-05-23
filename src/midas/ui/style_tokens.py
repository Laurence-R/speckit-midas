"""Shared style token access helpers for UI pages and components."""
from __future__ import annotations

from midas.ui.theme import get_palette, get_spacing_tokens


def spacing(name: str) -> int:
    """Return spacing token value by name.

    Supported names: spacing_s, spacing_m, spacing_l, container_padding.
    """
    tokens = get_spacing_tokens()
    if name not in tokens:
        raise KeyError(f"Unknown spacing token: {name}")
    return tokens[name]


def colors() -> dict[str, str]:
    """Return semantic palette for current appearance mode."""
    return get_palette()
