"""Main window layout: sidebar + content area + status bar."""
from __future__ import annotations

import customtkinter as ctk

from midas.ui.components.sidebar_nav import SidebarNav
from midas.ui.components.status_bar import StatusBar
from midas.ui.style_tokens import colors, spacing


class AppWindow(ctk.CTkFrame):
    """Root layout frame that holds SidebarNav, ContentArea, and StatusBar.

    Layout (1280 × 800):
    ┌──────────────────────────────┐
    │ SidebarNav (180px) │ Content │
    │                    │  Area   │
    ├────────────────────┴─────────┤
    │        StatusBar (28px)      │
    └──────────────────────────────┘
    """

    def __init__(
        self,
        master: ctk.CTk,
        on_navigate: "Callable[[str], None]",  # noqa: F821
        **kwargs: object,
    ) -> None:
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)
        palette = colors()
        self.configure(fg_color=palette["bg_primary"])

        # Status bar — bottom strip
        self.status_bar = StatusBar(self)
        self.status_bar.pack(side="bottom", fill="x")

        # Horizontal container for sidebar + content
        self._h_frame = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=palette["bg_primary"],
        )
        self._h_frame.pack(side="top", fill="both", expand=True)

        # Left sidebar
        self.sidebar = SidebarNav(self._h_frame, on_navigate=on_navigate)
        self.sidebar.pack(side="left", fill="y")

        # Right content area (pages stacked here)
        self.content_area = ctk.CTkFrame(
            self._h_frame,
            corner_radius=0,
            fg_color=palette["bg_primary"],
        )
        self.content_area.pack(side="left", fill="both", expand=True)
        self.content_area.pack_configure(padx=(0, spacing("spacing_m")), pady=(spacing("spacing_m"), 0))
