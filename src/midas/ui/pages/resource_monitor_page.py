"""ResourceMonitorPage: displays API quota status and local cache health."""
from __future__ import annotations

import os
import webbrowser
from datetime import date, datetime
from typing import TYPE_CHECKING

import customtkinter as ctk

from midas.ui.theme import get_palette, make_font

if TYPE_CHECKING:
    from midas.integrations.finmind_client import FinMindClient
    from midas.services.resource_monitor_service import ResourceMonitorService

_AI_STUDIO_URL = "https://aistudio.google.com/"


def _get_finmind_usage_state(finmind_client: "FinMindClient" | None) -> tuple[bool, int, int]:
    """Return token status and hourly usage with safe defaults."""
    if finmind_client is None:
        return False, 0, 600

    has_token = finmind_client.has_token()
    usage, limit = finmind_client.get_api_usage()
    return has_token, usage, limit


class ResourceMonitorPage(ctk.CTkFrame):
    """Read-only view of API quota status and local cache health."""

    def __init__(
        self,
        master,
        monitor_service: "ResourceMonitorService" | None = None,
        finmind_client: FinMindClient | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._monitor_service = monitor_service
        self._finmind = finmind_client
        self._build()

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build(self) -> None:
        palette = get_palette()
        self.configure(fg_color=palette["bg_primary"])

        ctk.CTkLabel(
            self,
            text="資源監控",
            font=make_font(size=18, weight="bold"),
            text_color=palette["text_primary"],
        ).pack(anchor="w", padx=20, pady=(16, 4))

        ctk.CTkLabel(
            self,
            text="即時顯示 API 配額、資料快取狀態",
            font=make_font(size=12),
            text_color=palette["text_secondary"],
        ).pack(anchor="w", padx=20, pady=(0, 16))

        self._build_gemini_section()
        self._build_finmind_section()
        self._build_cache_section()

        ctk.CTkButton(
            self,
            text="重新整理",
            width=120,
            font=make_font(size=13),
            command=self._refresh,
        ).pack(anchor="w", padx=20, pady=(8, 16))

    def _build_gemini_section(self) -> None:
        palette = get_palette()
        frame = self._make_section("Gemini AI（摘要生成）")

        key_row = ctk.CTkFrame(frame, fg_color="transparent")
        key_row.pack(fill="x", padx=12, pady=(4, 4))
        ctk.CTkLabel(
            key_row,
            text="Key 狀態：",
            font=make_font(size=13),
            text_color=palette["text_primary"],
        ).pack(side="left")
        self._gemini_key_label = ctk.CTkLabel(
            key_row,
            text="讀取中…",
            font=make_font(size=13),
            text_color=palette["text_secondary"],
        )
        self._gemini_key_label.pack(side="left")

        ctk.CTkButton(
            frame,
            text="↗ 前往 AI Studio 查看使用量",
            width=220,
            height=28,
            font=make_font(size=12),
            fg_color="transparent",
            border_width=1,
            command=lambda: webbrowser.open(_AI_STUDIO_URL),
        ).pack(anchor="w", padx=12, pady=(0, 10))

    def _build_finmind_section(self) -> None:
        palette = get_palette()
        frame = self._make_section("FinMind（市場資料）")

        token_row = ctk.CTkFrame(frame, fg_color="transparent")
        token_row.pack(fill="x", padx=12, pady=(4, 8))
        ctk.CTkLabel(
            token_row,
            text="Token 狀態：",
            font=make_font(size=13),
            text_color=palette["text_primary"],
        ).pack(side="left")
        self._finmind_token_label = ctk.CTkLabel(
            token_row,
            text="讀取中…",
            font=make_font(size=13),
            text_color=palette["text_secondary"],
        )
        self._finmind_token_label.pack(side="left")

        ctk.CTkLabel(
            frame,
            text="本小時 API 用量",
            font=make_font(size=12),
            text_color=palette["text_secondary"],
        ).pack(anchor="w", padx=12, pady=(0, 4))

        bar_row = ctk.CTkFrame(frame, fg_color="transparent")
        bar_row.pack(fill="x", padx=12, pady=(0, 2))
        self._finmind_bar = ctk.CTkProgressBar(bar_row, width=260)
        self._finmind_bar.set(0)
        self._finmind_bar.pack(side="left")
        self._finmind_usage_label = ctk.CTkLabel(
            bar_row,
            text="— / —",
            font=make_font(size=12),
            text_color=palette["text_primary"],
        )
        self._finmind_usage_label.pack(side="left", padx=(10, 0))

        ctk.CTkLabel(
            frame,
            text="每小時整點重置",
            font=make_font(size=11),
            text_color=palette["text_secondary"],
        ).pack(anchor="w", padx=12, pady=(0, 10))

    def _build_cache_section(self) -> None:
        palette = get_palette()
        frame = self._make_section("本機快取")

        last_row = ctk.CTkFrame(frame, fg_color="transparent")
        last_row.pack(fill="x", padx=12, pady=(4, 2))
        ctk.CTkLabel(
            last_row,
            text="最後更新：",
            font=make_font(size=13),
            text_color=palette["text_primary"],
        ).pack(side="left")
        self._cache_time_label = ctk.CTkLabel(
            last_row,
            text="—",
            font=make_font(size=13),
            text_color=palette["text_secondary"],
        )
        self._cache_time_label.pack(side="left")
        self._cache_dot_label = ctk.CTkLabel(
            last_row,
            text="",
            font=make_font(size=12),
            text_color=palette["text_secondary"],
        )
        self._cache_dot_label.pack(side="left", padx=(10, 0))

        self._cache_counts_label = ctk.CTkLabel(
            frame,
            text="讀取中…",
            font=make_font(size=12),
            text_color=palette["text_secondary"],
        )
        self._cache_counts_label.pack(anchor="w", padx=12, pady=(2, 2))

        self._cache_size_label = ctk.CTkLabel(
            frame,
            text="",
            font=make_font(size=12),
            text_color=palette["text_secondary"],
        )
        self._cache_size_label.pack(anchor="w", padx=12, pady=(0, 10))

    def _make_section(self, title: str) -> ctk.CTkFrame:
        palette = get_palette()
        outer = ctk.CTkFrame(self, fg_color=palette["bg_secondary"], corner_radius=8)
        outer.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(
            outer,
            text=title,
            font=make_font(size=14, weight="bold"),
            text_color=palette["text_primary"],
        ).pack(anchor="w", padx=12, pady=(10, 4))
        return outer

    # ------------------------------------------------------------------
    # Refresh logic
    # ------------------------------------------------------------------

    def load(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self._refresh_gemini()
        self._refresh_finmind()
        self._refresh_cache()

    def _refresh_gemini(self) -> None:
        palette = get_palette()
        has_key = False
        if self._monitor_service is not None:
            has_key = self._monitor_service.get_snapshot().has_gemini_key

        key_text = "已設定 ✓" if has_key else "未設定（AI 摘要功能不可用）"
        key_color = palette["success"] if has_key else palette["warning"]
        self._gemini_key_label.configure(text=key_text, text_color=key_color)

    def _refresh_finmind(self) -> None:
        palette = get_palette()
        has_token, usage, limit = _get_finmind_usage_state(self._finmind)

        token_text = "已設定 ✓" if has_token else "未設定（市場資料不可用）"
        token_color = palette["success"] if has_token else palette["warning"]
        self._finmind_token_label.configure(text=token_text, text_color=token_color)

        safe_limit = limit if limit > 0 else 600
        pct = usage / safe_limit
        if pct >= 1.0:
            bar_color = palette["error"]
        elif pct >= 0.7:
            bar_color = palette["warning"]
        else:
            bar_color = palette["success"]

        self._finmind_bar.set(min(pct, 1.0))
        self._finmind_bar.configure(progress_color=bar_color)
        self._finmind_usage_label.configure(
            text=f"{usage} / {safe_limit} 次/小時",
            text_color=bar_color,
        )

    def _refresh_cache(self) -> None:
        palette = get_palette()
        if self._monitor_service is None:
            return
        try:
            snapshot = self._monitor_service.get_snapshot()
            if snapshot.last_success_at is not None:
                last_dt = snapshot.last_success_at
                delta_days = (date.today() - last_dt.date()).days
                if delta_days == 0:
                    dot_text, dot_color = "● 今日已更新", palette["success"]
                elif delta_days == 1:
                    dot_text, dot_color = "● 昨日資料", palette["warning"]
                else:
                    dot_text, dot_color = f"● {delta_days} 天前", palette["error"]
                self._cache_time_label.configure(
                    text=last_dt.strftime("%Y-%m-%d %H:%M"),
                    text_color=palette["text_primary"],
                )
                self._cache_dot_label.configure(text=dot_text, text_color=dot_color)
            else:
                self._cache_time_label.configure(
                    text="尚無更新紀錄", text_color=palette["text_secondary"]
                )
                self._cache_dot_label.configure(text="● 未更新", text_color=palette["error"])

            self._cache_counts_label.configure(
                text=(
                    f"市場事件：{snapshot.market_event_count} 筆  ·  "
                    f"財務指標：{snapshot.financial_metric_count} 筆  ·  "
                    f"大盤概況：{snapshot.market_overview_count} 筆"
                ),
                text_color=palette["text_secondary"],
            )

            if snapshot.db_size_mb is not None:
                self._cache_size_label.configure(text=f"DB 大小：{snapshot.db_size_mb:.1f} MB")
            else:
                self._cache_size_label.configure(text="DB 大小：未知")
        except Exception:
            pass
