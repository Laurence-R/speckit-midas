"""StockEventCard: displays a single event with AI summary and source link."""
from __future__ import annotations

import re
import webbrowser
from typing import Callable

import customtkinter as ctk

from midas.models.market_event import MarketEvent, Sentiment
from midas.ui.style_tokens import spacing
from midas.ui.theme import get_palette, make_font

_SENTIMENT_LABELS: dict[Sentiment, str] = {
    Sentiment.POSITIVE: "正面",
    Sentiment.NEUTRAL:  "中性",
    Sentiment.NEGATIVE: "負面",
}


class StockEventCard(ctk.CTkFrame):
    """Full event card: title, badge, AI summary (on-demand), source, disclaimer."""

    def __init__(
        self,
        master,
        event: MarketEvent,
        on_analyze: Callable[[MarketEvent, Callable[[MarketEvent], None]], None] | None = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._event = event
        self._on_analyze = on_analyze
        self._badge_row: ctk.CTkFrame | None = None
        self._sentiment_badge: ctk.CTkLabel | None = None
        self._summary_area: ctk.CTkFrame | None = None
        self._build()

    def _build(self) -> None:
        palette = get_palette()
        self.configure(
            fg_color=palette["bg_card"],
            corner_radius=8,
            border_width=1,
            border_color=palette["border"],
        )

        # Title
        ctk.CTkLabel(
            self,
            text=self._event.title,
            font=make_font(size=13, weight="bold"),
            text_color=palette["text_primary"],
            wraplength=500,
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=spacing("spacing_m"), pady=(spacing("spacing_m"), 2))

        # Badge row: event type + sentiment (added later when AI completes)
        self._badge_row = ctk.CTkFrame(self, fg_color="transparent")
        self._badge_row.pack(fill="x", padx=spacing("spacing_m"), pady=2)

        ctk.CTkLabel(
            self._badge_row,
            text=self._event.event_type.display_label,
            font=make_font(size=10),
            fg_color=palette["bg_secondary"],
            text_color=palette["text_secondary"],
            corner_radius=4,
            padx=6,
        ).pack(side="left")

        if self._event.sentiment:
            self._add_sentiment_badge(self._event.sentiment)

        # Summary area (rebuilt dynamically on AI analysis)
        self._summary_area = ctk.CTkFrame(self, fg_color="transparent")
        self._summary_area.pack(fill="x")
        self._render_summary_area()

        # Source + time
        pub_time = self._event.occurred_at.strftime("%Y-%m-%d %H:%M")
        ctk.CTkLabel(
            self,
            text=f"來源：{self._event.source_name}  ·  {pub_time}",
            font=make_font(size=10),
            text_color=palette["text_secondary"],
        ).pack(anchor="w", padx=spacing("spacing_m"), pady=(2, 0))

        # View original button
        ctk.CTkButton(
            self,
            text="查看原文",
            width=100,
            font=make_font(size=12),
            command=lambda: webbrowser.open(self._event.source_url),
            fg_color=palette["bg_secondary"],
            hover_color=palette["interactive_hover"],
            border_width=1,
            border_color=palette["border"],
            text_color=palette["text_primary"],
        ).pack(anchor="w", padx=spacing("spacing_m"), pady=spacing("spacing_s"))

        # Disclaimer
        ctk.CTkLabel(
            self,
            text=self._event.disclaimer,
            font=make_font(size=9),
            text_color=palette["text_secondary"],
        ).pack(anchor="w", padx=spacing("spacing_m"), pady=(0, spacing("spacing_m")))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_sentiment_badge(self, sentiment: Sentiment) -> None:
        if self._sentiment_badge is not None:
            self._sentiment_badge.destroy()
        palette = get_palette()
        color_map = {
            Sentiment.POSITIVE: palette["sentiment_positive"],
            Sentiment.NEUTRAL: palette["sentiment_neutral"],
            Sentiment.NEGATIVE: palette["sentiment_negative"],
        }
        color = color_map.get(sentiment, palette["sentiment_neutral"])
        self._sentiment_badge = ctk.CTkLabel(
            self._badge_row,
            text=_SENTIMENT_LABELS.get(sentiment, ""),
            font=make_font(size=10),
            fg_color=color,
            text_color="#ffffff",
            corner_radius=4,
            padx=6,
        )
        self._sentiment_badge.pack(side="left", padx=(6, 0))

    def _render_summary_area(self) -> None:
        """Clear and rebuild the summary section based on current event state."""
        for w in self._summary_area.winfo_children():
            w.destroy()

        palette = get_palette()

        if self._event.ai_summary:
            self._render_summary_textbox(palette)
            if self._on_analyze is not None:
                btn = ctk.CTkButton(
                    self._summary_area,
                    text="🔄 重新分析",
                    width=90,
                    height=24,
                    font=make_font(size=11),
                    fg_color="transparent",
                    border_width=1,
                    text_color=palette["text_secondary"],
                )
                btn.configure(command=lambda b=btn: self._start_analysis(b))
                btn.pack(anchor="w", padx=spacing("spacing_m"), pady=(2, spacing("spacing_s") // 2))
        elif self._on_analyze is not None:
            btn = ctk.CTkButton(
                self._summary_area,
                text="✨ AI 分析",
                width=100,
                font=make_font(size=12),
            )
            btn.configure(command=lambda b=btn: self._start_analysis(b))
            btn.pack(anchor="w", padx=spacing("spacing_m"), pady=(spacing("spacing_s"), 2))

    def _render_summary_textbox(self, palette: dict) -> None:
        """Render ai_summary in a read-only CTkTextbox with bold 【】 section headers."""
        text = self._event.ai_summary or ""
        # Estimate height from line count + text length
        lines = text.split("\n")
        line_count = sum(1 + max(len(ln) - 1, 0) // 52 for ln in lines)
        height = min(max(line_count * 20, 80), 340)

        box = ctk.CTkTextbox(
            self._summary_area,
            font=make_font(size=12),
            text_color=palette["text_primary"],
            fg_color=palette["bg_card"],
            border_width=0,
            wrap="word",
            height=height,
            activate_scrollbars=False,
        )
        box.insert("1.0", text)

        # Bold 【...】 section headers
        inner = box._textbox  # underlying tk.Text
        inner.tag_configure("header", font=make_font(size=12, weight="bold"))
        for match in re.finditer(r"【[^】]+】", text):
            before = text[: match.start()]
            line_num = before.count("\n") + 1
            col = match.start() - (before.rfind("\n") + 1)
            inner.tag_add("header", f"{line_num}.{col}", f"{line_num}.{col + len(match.group())}")

        box.configure(state="disabled")
        box.pack(fill="x", padx=spacing("spacing_m"), pady=(spacing("spacing_s"), 2))

    def _start_analysis(self, btn: ctk.CTkButton) -> None:
        """Replace summary area with a progress bar, then invoke the on_analyze callback."""
        self._event.ai_summary = None  # force re-analysis

        # Show loading UI in summary area
        for w in self._summary_area.winfo_children():
            w.destroy()
        palette = get_palette()
        ctk.CTkLabel(
            self._summary_area,
            text="✨ AI 分析中...",
            font=make_font(size=12),
            text_color=palette["text_secondary"],
        ).pack(anchor="w", padx=spacing("spacing_m"), pady=(spacing("spacing_s"), 2))
        bar = ctk.CTkProgressBar(self._summary_area, mode="indeterminate", width=300)
        bar.pack(anchor="w", padx=spacing("spacing_m"), pady=(0, spacing("spacing_s")))
        bar.start()

        def on_done(updated_event: MarketEvent) -> None:
            bar.stop()
            self._event = updated_event
            if updated_event.sentiment:
                self._add_sentiment_badge(updated_event.sentiment)
            self._render_summary_area()

        self._on_analyze(self._event, on_done)
