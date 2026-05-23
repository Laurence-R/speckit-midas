"""MarketOverviewCard: displays the TWSE index summary and sector rankings."""
from __future__ import annotations

import customtkinter as ctk

from midas.models.market_overview import MarketOverview
from midas.ui.style_tokens import spacing
from midas.ui.theme import get_palette, make_font


class MarketOverviewCard(ctk.CTkFrame):
    """Displays TWSE weighted index, volume, institutional flows, and top sectors."""

    def __init__(self, master, overview: MarketOverview | None = None, **kwargs):
        super().__init__(master, **kwargs)
        self._overview = overview
        self._build()

    def _build(self) -> None:
        palette = get_palette()
        self.configure(
            fg_color=palette["bg_card"],
            corner_radius=8,
            border_width=1,
            border_color=palette["border"],
        )

        if self._overview is None:
            ctk.CTkLabel(
                self,
                text="暫無大盤資料",
                font=make_font(size=12),
                text_color=palette["text_secondary"],
            ).pack(pady=spacing("spacing_l"))
            return

        inst = self._overview.institutional or {}
        foreign_net = inst.get("foreign_investor_net", 0)
        trust_net = inst.get("investment_trust_net", 0)
        dealer_net = inst.get("dealer_net", 0)

        # Title
        ctk.CTkLabel(
            self,
            text="加權指數",
            font=make_font(size=13, weight="bold"),
            text_color=palette["text_primary"],
        ).pack(anchor="w", padx=12, pady=(10, 0))

        # Close price
        ctk.CTkLabel(
            self,
            text=f"{self._overview.taiex_close:,.2f}",
            font=make_font(size=22, weight="bold"),
            text_color=palette["text_primary"],
        ).pack(anchor="w", padx=spacing("spacing_m"))

        # Change / change pct
        chg = self._overview.taiex_change
        pct = self._overview.taiex_change_pct
        sign = "+" if chg >= 0 else ""
        chg_color = palette["sentiment_positive"] if chg >= 0 else palette["sentiment_negative"]
        ctk.CTkLabel(
            self,
            text=f"{sign}{chg:,.2f}  ({sign}{pct:.2f}%)",
            font=make_font(size=12),
            text_color=chg_color,
        ).pack(anchor="w", padx=spacing("spacing_m"), pady=(0, spacing("spacing_s") // 2))

        # Volume
        vol_text = f"成交量 {self._overview.volume_b:,.0f} 億"
        if self._overview.volume_5d_avg_b:
            vol_text += f"   五日均量 {self._overview.volume_5d_avg_b:,.0f} 億"
        ctk.CTkLabel(
            self,
            text=vol_text,
            font=make_font(size=11),
            text_color=palette["text_secondary"],
        ).pack(anchor="w", padx=spacing("spacing_m"), pady=(0, spacing("spacing_s")))

        # Institutional flows
        inst_text = (
            f"外資: {foreign_net:+,.2f}  投信: {trust_net:+,.2f}  自營: {dealer_net:+,.2f}"
        )
        ctk.CTkLabel(
            self,
            text=inst_text,
            font=make_font(size=11),
            text_color=palette["text_secondary"],
        ).pack(anchor="w", padx=spacing("spacing_m"))

        # Sector rankings (top 5)
        sectors = self._overview.sector_rankings or []
        if sectors:
            ctk.CTkLabel(
                self,
                text="類股排行",
                font=make_font(size=12, weight="bold"),
                text_color=palette["text_primary"],
            ).pack(anchor="w", padx=spacing("spacing_m"), pady=(spacing("spacing_s"), 2))
            for s in sectors[:5]:
                name = s.get("name", "")
                pct_s = s.get("change_pct", 0.0)
                color = (
                    palette["sentiment_positive"] if pct_s >= 0
                    else palette["sentiment_negative"]
                )
                ctk.CTkLabel(
                    self,
                    text=f"{name}  {pct_s:+.2f}%",
                    text_color=color,
                    font=make_font(size=11),
                ).pack(anchor="w", padx=spacing("container_padding"))

        ctk.CTkFrame(self, height=spacing("spacing_s"), fg_color="transparent").pack()

    def update_data(self, overview: MarketOverview | None) -> None:
        for w in self.winfo_children():
            w.destroy()
        self._overview = overview
        self._build()
