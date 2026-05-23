"""StockDetailPage: shows events and financial metrics for a single stock."""
from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Callable

import customtkinter as ctk

from midas.models.financial_metric import MetricType
from midas.models.market_event import MarketEvent
from midas.ui.components.financial_metric_row import FinancialMetricRow
from midas.ui.components.stock_event_card import StockEventCard
from midas.ui.style_tokens import spacing
from midas.ui.theme import get_palette, make_font
from midas.viewmodels.stock_detail_vm import StockDetailViewModel

if TYPE_CHECKING:
    from midas.agents.summarization_agent import SummarizationAgent
    from midas.repositories.interfaces import IMarketEventRepository

logger = logging.getLogger(__name__)

_TAB_EVENTS  = "事件"
_TAB_METRICS = "財務指標"


class StockDetailPage(ctk.CTkFrame):
    """Individual stock detail: Events tab + Financial Metrics tab."""

    def __init__(
        self,
        master,
        view_model: StockDetailViewModel | None = None,
        summarization_agent: SummarizationAgent | None = None,
        event_repo: IMarketEventRepository | None = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._vm = view_model
        self._summarization_agent = summarization_agent
        self._event_repo = event_repo
        self._current_symbol: str = ""
        self._tabview: ctk.CTkTabview | None = None
        self._build_skeleton()

    def _build_skeleton(self) -> None:
        palette = get_palette()
        self.configure(fg_color=palette["bg_primary"])

        self._title = ctk.CTkLabel(
            self,
            text="股票詳情",
            font=make_font(size=18, weight="bold"),
            text_color=palette["text_primary"],
        )
        self._title.pack(anchor="w", padx=spacing("container_padding"), pady=(spacing("spacing_m"), spacing("spacing_s")))

        self._tabview = ctk.CTkTabview(
            self,
            fg_color=palette["bg_secondary"],
            segmented_button_selected_color=palette["accent"],
            segmented_button_selected_hover_color=palette["interactive_hover"],
            segmented_button_unselected_color=palette["bg_card"],
            segmented_button_unselected_hover_color=palette["interactive_hover"],
            text_color=palette["text_primary"],
            border_width=1,
            border_color=palette["border"],
        )
        self._tabview.pack(fill="both", expand=True, padx=spacing("container_padding"), pady=(0, spacing("spacing_m")))
        self._tabview.add(_TAB_EVENTS)
        self._tabview.add(_TAB_METRICS)

        self._events_frame = ctk.CTkScrollableFrame(
            self._tabview.tab(_TAB_EVENTS), fg_color=palette["bg_primary"],
        )
        self._events_frame.pack(fill="both", expand=True)

        self._metrics_frame = ctk.CTkScrollableFrame(
            self._tabview.tab(_TAB_METRICS), fg_color=palette["bg_primary"],
        )
        self._metrics_frame.pack(fill="both", expand=True)

    def load(self, symbol: str = "") -> None:
        """Load event and financial data for *symbol*."""
        self._current_symbol = symbol
        self._title.configure(
            text=f"{symbol} 股票詳情" if symbol else "股票詳情"
        )
        if self._vm is None or not symbol:
            return
        self._load_events(symbol)
        self._load_metrics(symbol)

    def _load_events(self, symbol: str) -> None:
        palette = get_palette()
        for w in self._events_frame.winfo_children():
            w.destroy()

        events = self._vm.load_events(symbol)
        if not events:
            ctk.CTkLabel(
                self._events_frame,
                text="暫無事件",
                text_color=palette["text_secondary"],
                font=make_font(size=13),
            ).pack(pady=spacing("spacing_l") * 2)
            return

        for evt in events:
            on_analyze = self._make_analyze_callback() if self._summarization_agent else None
            StockEventCard(self._events_frame, event=evt, on_analyze=on_analyze).pack(
                fill="x",
                pady=spacing("spacing_s") // 2,
            )

    def _load_metrics(self, symbol: str) -> None:
        palette = get_palette()
        for w in self._metrics_frame.winfo_children():
            w.destroy()

        metrics_by_type = self._vm.load_metrics(symbol)
        for metric_type in MetricType:
            rows = metrics_by_type.get(metric_type.value, [])
            FinancialMetricRow(
                self._metrics_frame, metric_type=metric_type, metrics=rows,
            ).pack(fill="x", pady=spacing("spacing_s") // 2)

    # ------------------------------------------------------------------
    # On-demand AI analysis
    # ------------------------------------------------------------------

    def _make_analyze_callback(
        self,
    ) -> Callable[[MarketEvent, Callable[[MarketEvent], None]], None]:
        """Return an on_analyze callback that runs AI in a background thread."""

        def on_analyze(
            event: MarketEvent,
            on_done: Callable[[MarketEvent], None],
        ) -> None:
            def run() -> None:
                try:
                    results = self._summarization_agent.summarize_events(event.symbol, [event])
                    updated = results[0]
                    if updated.ai_summary and self._event_repo is not None:
                        self._event_repo.update_summary(updated)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("On-demand AI analysis failed: %s", exc)
                    updated = event
                self.after(0, lambda: on_done(updated))

            threading.Thread(target=run, daemon=True).start()

        return on_analyze
