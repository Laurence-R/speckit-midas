"""DashboardPage: shows market overview and today's stock events."""
from __future__ import annotations

import customtkinter as ctk

from midas.ui.components.event_list_item import EventListItem
from midas.ui.components.market_overview_card import MarketOverviewCard
from midas.ui.theme import get_palette, make_font
from midas.viewmodels.dashboard_vm import DashboardViewModel


class DashboardPage(ctk.CTkFrame):
    """Main dashboard: market overview card + today's event list."""

    def __init__(
        self,
        master,
        view_model: DashboardViewModel | None = None,
        controller=None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._vm = view_model
        self._controller = controller
        self._overview_card: MarketOverviewCard | None = None
        self._list_frame: ctk.CTkScrollableFrame | None = None
        self._build_skeleton()

    def _build_skeleton(self) -> None:
        palette = get_palette()
        self.configure(fg_color=palette["bg_primary"])

        ctk.CTkLabel(
            self,
            text="今日重要事件",
            font=make_font(size=18, weight="bold"),
            text_color=palette["text_primary"],
        ).pack(anchor="w", padx=20, pady=(16, 8))

        self._overview_card = MarketOverviewCard(self, overview=None)
        self._overview_card.pack(fill="x", padx=20, pady=(0, 12))

        self._list_frame = ctk.CTkScrollableFrame(
            self, fg_color=palette["bg_primary"], corner_radius=0
        )
        self._list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 12))

    def load(self) -> None:
        """Populate the page from the ViewModel."""
        if self._vm is None:
            return

        overview = self._vm.get_market_overview()
        self._overview_card.update_data(overview)

        for w in self._list_frame.winfo_children():
            w.destroy()

        groups = self._vm.get_today_events()
        if not groups:
            ctk.CTkLabel(
                self._list_frame,
                text="今日暫無事件",
                text_color=get_palette()["text_secondary"],
                font=make_font(size=13),
            ).pack(pady=40)
            return

        for group in groups:
            item = EventListItem(
                self._list_frame,
                stock=group.stock,
                events=group.events,
                on_click=self._on_stock_click,
            )
            item.pack(fill="x", pady=4)

    def _on_stock_click(self, symbol: str) -> None:
        if self._controller:
            self._controller.show_stock_detail(symbol)
