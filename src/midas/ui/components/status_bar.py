"""Bottom status bar component."""
from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from midas.ui.theme import get_palette, make_font


class StatusBar(ctk.CTkFrame):
    """Bottom status bar showing update progress, timestamp, and retry button."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkFrame,
        on_retry: Callable[[], None] | None = None,
        **kwargs: object,
    ) -> None:
        kwargs.setdefault("height", 28)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)
        self._on_retry = on_retry

        palette = get_palette()

        self._status_label = ctk.CTkLabel(
            self,
            text="就緒",
            font=make_font(size=12),
            text_color=palette["text_secondary"],
            anchor="w",
        )
        self._status_label.pack(side="left", padx=10, pady=2)

        self._retry_btn = ctk.CTkButton(
            self,
            text="手動更新",
            width=80,
            height=22,
            font=make_font(size=12),
            command=self._handle_retry,
        )
        self._retry_btn.pack(side="right", padx=6, pady=2)

        self._time_label = ctk.CTkLabel(
            self,
            text="",
            font=make_font(size=12),
            text_color=palette["text_secondary"],
            anchor="e",
        )
        self._time_label.pack(side="right", padx=10, pady=2)

    def set_retry_command(self, command: Callable[[], None]) -> None:
        self._on_retry = command

    def update_progress(self, step: int, total: int, label: str) -> None:
        self._status_label.configure(text=f"更新中 {step}/{total}  {label}")
        self._retry_btn.configure(state="disabled", text="更新中…")

    def show_error(self, msg: str) -> None:
        self._status_label.configure(text=f"更新失敗：{msg}")
        self._retry_btn.configure(state="normal", text="重試")

    def show_ready(self, timestamp: str) -> None:
        self._status_label.configure(text="就緒")
        self._time_label.configure(text=f"最後更新：{timestamp}")
        self._retry_btn.configure(state="normal", text="手動更新")

    def _handle_retry(self) -> None:
        if self._on_retry:
            self._on_retry()
