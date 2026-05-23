"""EventListItem: a clickable row showing one tracked stock's event summary."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from midas.models.market_event import EventType, MarketEvent
from midas.models.tracked_stock import TrackedStock
from midas.ui.style_tokens import spacing
from midas.ui.theme import get_palette, make_font

_TYPE_LABELS: dict[EventType, str] = {
    EventType.FINANCIAL_REPORT:     "財報",
    EventType.INVESTOR_CONFERENCE:  "法說會",
    EventType.MATERIAL_NEWS:        "重大訊息",
    EventType.GENERAL_ANNOUNCEMENT: "一般公告",
}
_TYPE_COLORS: dict[EventType, str] = {
    EventType.FINANCIAL_REPORT:     "#0EA5E9",
    EventType.INVESTOR_CONFERENCE:  "#6366F1",
    EventType.MATERIAL_NEWS:        "#DC2626",
    EventType.GENERAL_ANNOUNCEMENT: "#4A6585",
}


class EventListItem(ctk.CTkFrame):
    """Displays company name, symbol, event type badge, time, and AI summary preview."""

    def __init__(
        self,
        master,
        stock: TrackedStock,
        events: list[MarketEvent],
        on_click: Callable[[str], None] | None = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._stock = stock
        self._events = events
        self._on_click = on_click
        self._build()

    def _build(self) -> None:
        palette = get_palette()
        self.configure(
            fg_color=palette["bg_secondary"],
            corner_radius=6,
            cursor="hand2" if self._on_click else "",
            border_width=1,
            border_color=palette["border"],
        )
        self.bind("<Button-1>", self._handle_click)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=spacing("spacing_m"), pady=spacing("spacing_s"))

        # Symbol + company name
        name_label = ctk.CTkLabel(
            row,
            text=f"{self._stock.symbol}  {self._stock.company_name}",
            font=make_font(size=13, weight="bold"),
            text_color=palette["text_primary"],
        )
        name_label.pack(side="left")
        name_label.bind("<Button-1>", self._handle_click)

        # Event type badge
        if self._events:
            evt = self._events[0]
            badge_color = _TYPE_COLORS.get(evt.event_type, "#607d8b")
            badge = ctk.CTkLabel(
                row,
                text=_TYPE_LABELS.get(evt.event_type, evt.event_type.value),
                font=make_font(size=10),
                fg_color=badge_color,
                text_color="#ffffff",
                corner_radius=4,
                padx=6,
            )
            badge.pack(side="left", padx=(spacing("spacing_s"), 0))
            badge.bind("<Button-1>", self._handle_click)

        # Time
        if self._events:
            time_str = self._events[0].occurred_at.strftime("%H:%M")
            ctk.CTkLabel(
                row,
                text=time_str,
                font=make_font(size=10),
                text_color=palette["text_secondary"],
            ).pack(side="right")

        # AI summary preview (first 50 chars)
        if self._events and self._events[0].ai_summary:
            preview = self._events[0].ai_summary[:50]
            if len(self._events[0].ai_summary) > 50:
                preview += "…"
            summary_label = ctk.CTkLabel(
                self,
                text=preview,
                font=make_font(size=11),
                text_color=palette["text_secondary"],
                anchor="w",
            )
            summary_label.pack(fill="x", padx=spacing("spacing_m"), pady=(0, spacing("spacing_s")))
            summary_label.bind("<Button-1>", self._handle_click)

    def _handle_click(self, _event=None) -> None:
        if self._on_click:
            self._on_click(self._stock.symbol)
