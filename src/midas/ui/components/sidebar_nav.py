"""Left sidebar navigation component."""
from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from midas.ui.theme import get_palette, make_font
from midas.ui.style_tokens import spacing

_NAV_ITEMS: list[tuple[str, str]] = [
    ("首頁", "dashboard"),
    ("自選股", "watchlist"),
    ("資源監控", "resource_monitor"),
    ("設定", "settings"),
]


class SidebarNav(ctk.CTkFrame):
    """Left-side navigation panel with page-switch buttons."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkFrame,
        on_navigate: Callable[[str], None],
        **kwargs: object,
    ) -> None:
        kwargs.setdefault("width", 180)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)
        self._on_navigate = on_navigate
        self._buttons: dict[str, ctk.CTkButton] = {}

        palette = get_palette()
        self.configure(fg_color=palette["bg_secondary"])

        ctk.CTkLabel(
            self,
            text="Midas",
            font=make_font(size=20, weight="bold"),
            text_color=palette["accent"],
        ).pack(pady=(spacing("spacing_l"), spacing("spacing_l")), padx=spacing("spacing_m"))

        for label, page_name in _NAV_ITEMS:
            btn = ctk.CTkButton(
                self,
                text=label,
                font=make_font(size=13),
                command=lambda p=page_name: self._on_navigate(p),
                anchor="w",
                corner_radius=6,
                fg_color=palette["bg_card"],
                hover_color=palette["interactive_hover"],
                text_color=palette["text_primary"],
                border_width=1,
                border_color=palette["border"],
            )
            btn.pack(fill="x", padx=spacing("spacing_m"), pady=(0, spacing("spacing_s")))
            self._buttons[page_name] = btn

    def set_active(self, page_name: str) -> None:
        """Visually highlight the active navigation button."""
        palette = get_palette()
        for name, btn in self._buttons.items():
            if name == page_name:
                btn.configure(
                    fg_color=palette["accent"],
                    text_color=palette["bg_primary"],
                    border_color=palette["accent"],
                )
            else:
                btn.configure(
                    fg_color=palette["bg_card"],
                    text_color=palette["text_primary"],
                    border_color=palette["border"],
                )
