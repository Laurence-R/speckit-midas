"""SettingsPage: API keys, theme toggle, font size, and cache management."""
from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from midas.ui.theme import (
    apply_theme,
    get_font_scale,
    get_palette,
    make_font,
    set_font_scale,
)

# Maps segmented-button label → font scale offset
_FONT_SCALE_MAP: dict[str, int] = {"小": -2, "中": 0, "大": 2}
_FONT_SCALE_LABEL: dict[int, str] = {v: k for k, v in _FONT_SCALE_MAP.items()}


class SettingsPage(ctk.CTkFrame):
    """Application settings: API keys, theme, font size, and cache control."""

    def __init__(
        self,
        master,
        db_conn=None,
        on_rebuild: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._db = db_conn
        self._on_rebuild = on_rebuild
        self._build()

    def _build(self) -> None:
        palette = get_palette()
        self.configure(fg_color=palette["bg_primary"])

        # ---- Page title ----
        ctk.CTkLabel(
            self,
            text="設定",
            font=make_font(size=18, weight="bold"),
            text_color=palette["text_primary"],
        ).pack(anchor="w", padx=20, pady=(16, 4))

        # ---- API Keys section ----
        self._section_label("API 金鑰")
        form = ctk.CTkFrame(self, fg_color=palette["bg_card"], corner_radius=8)
        form.pack(fill="x", padx=20, pady=(0, 16))
        self._add_setting_row(form, "FinMind Token", "finmind_token", show=False)
        self._add_setting_row(form, "Gemini API Key", "gemini_api_key", show=False)

        # ---- Appearance section ----
        self._section_label("外觀")
        appearance_frame = ctk.CTkFrame(self, fg_color=palette["bg_card"], corner_radius=8)
        appearance_frame.pack(fill="x", padx=20, pady=(0, 16))

        # Theme toggle
        theme_row = ctk.CTkFrame(appearance_frame, fg_color="transparent")
        theme_row.pack(fill="x", padx=12, pady=(8, 4))
        ctk.CTkLabel(
            theme_row, text="主題", width=160, anchor="w",
            font=make_font(size=13), text_color=palette["text_primary"],
        ).pack(side="left")
        ctk.CTkSegmentedButton(
            theme_row,
            values=["深色", "淺色"],
            command=self._on_theme_change,
        ).pack(side="left")

        # Font size
        font_row = ctk.CTkFrame(appearance_frame, fg_color="transparent")
        font_row.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(
            font_row, text="字體大小", width=160, anchor="w",
            font=make_font(size=13), text_color=palette["text_primary"],
        ).pack(side="left")
        current_label = _FONT_SCALE_LABEL.get(get_font_scale(), "中")
        self._font_seg = ctk.CTkSegmentedButton(
            font_row,
            values=["小", "中", "大"],
            command=self._on_font_change,
        )
        self._font_seg.set(current_label)
        self._font_seg.pack(side="left")

        # ---- Other section ----
        self._section_label("其他")
        other_frame = ctk.CTkFrame(self, fg_color=palette["bg_card"], corner_radius=8)
        other_frame.pack(fill="x", padx=20, pady=(0, 16))
        cache_row = ctk.CTkFrame(other_frame, fg_color="transparent")
        cache_row.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(
            cache_row, text="清除快取", width=160, anchor="w",
            font=make_font(size=13), text_color=palette["text_primary"],
        ).pack(side="left")
        ctk.CTkButton(
            cache_row,
            text="清除",
            width=80,
            fg_color=palette["error"],
            hover_color="#B91C1C",
            command=self._on_clear_cache,
        ).pack(side="left")
        self._cache_feedback_label = ctk.CTkLabel(
            cache_row, text="", font=make_font(size=12), text_color=palette["success"],
        )
        self._cache_feedback_label.pack(side="left", padx=(8, 0))

    def load(self) -> None:
        pass  # reload settings from DB if needed

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _section_label(self, text: str) -> None:
        palette = get_palette()
        ctk.CTkLabel(
            self,
            text=text,
            font=make_font(size=11, weight="bold"),
            text_color=palette["text_secondary"],
        ).pack(anchor="w", padx=24, pady=(4, 2))

    def _add_setting_row(self, parent, label: str, db_key: str, show: bool = True) -> None:
        palette = get_palette()
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(
            row, text=label, width=160, anchor="w",
            font=make_font(size=13), text_color=palette["text_primary"],
        ).pack(side="left")
        entry = ctk.CTkEntry(row, width=300, show="*" if not show else "")
        entry.pack(side="left")

        if self._db is not None:
            try:
                db_row = self._db.execute(
                    "SELECT value FROM app_settings WHERE key = ?", (db_key,)
                ).fetchone()
                if db_row and db_row["value"]:
                    entry.insert(0, db_row["value"])
            except Exception:
                pass

        saved_label = ctk.CTkLabel(
            row, text="", font=make_font(size=11), text_color=palette["success"],
        )
        saved_label.pack(side="left", padx=(6, 0))

        def _save(e=entry, k=db_key, lbl=saved_label) -> None:
            self._save_setting(k, e.get())
            lbl.configure(text="已儲存")
            lbl.after(2000, lambda: lbl.configure(text=""))

        ctk.CTkButton(
            row, text="儲存", width=60, font=make_font(size=12), command=_save,
        ).pack(side="left", padx=(8, 0))

    def _save_setting(self, key: str, value: str) -> None:
        if self._db is None:
            return
        self._db.execute(
            "UPDATE app_settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?",
            (value, key),
        )
        self._db.commit()

    def _on_theme_change(self, mode: str) -> None:
        apply_theme("dark" if mode == "深色" else "light")

    def _on_font_change(self, label: str) -> None:
        scale = _FONT_SCALE_MAP.get(label, 0)
        set_font_scale(scale)
        if self._db is not None:
            try:
                self._db.execute(
                    "INSERT OR REPLACE INTO app_settings(key, value, updated_at)"
                    " VALUES (?, ?, CURRENT_TIMESTAMP)",
                    ("font_scale", str(scale)),
                )
                self._db.commit()
            except Exception:
                pass
        if self._on_rebuild is not None:
            self._on_rebuild()

    def _on_clear_cache(self) -> None:
        from tkinter import messagebox
        if not messagebox.askyesno(
            "確認清除",
            "將清除所有快取資料（市場事件、財務數據、大盤概況），確定繼續？",
        ):
            return
        if self._db is None:
            return
        self._db.execute("DELETE FROM market_events")
        self._db.execute("DELETE FROM financial_metrics")
        self._db.execute("DELETE FROM market_overviews")
        self._db.commit()
        self._cache_feedback_label.configure(text="已清除")
        self._cache_feedback_label.after(2000, lambda: self._cache_feedback_label.configure(text=""))

