"""FinancialMetricRow: displays a trend table for one financial metric."""
from __future__ import annotations

import customtkinter as ctk

from midas.models.financial_metric import Direction, FinancialMetric, MetricType
from midas.ui.style_tokens import spacing
from midas.ui.theme import get_palette, make_font

_DIRECTION_ARROWS: dict[Direction, str] = {
    Direction.IMPROVING: "↑",
    Direction.STABLE:    "→",
    Direction.DECLINING: "↓",
}


class FinancialMetricRow(ctk.CTkFrame):
    """Shows metric name, period values, direction arrows, and data source info."""

    def __init__(
        self,
        master,
        metric_type: MetricType,
        metrics: list[FinancialMetric],
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._metric_type = metric_type
        self._metrics = metrics
        self._build()

    def _build(self) -> None:
        palette = get_palette()
        self.configure(
            fg_color=palette["bg_secondary"],
            corner_radius=6,
            border_width=1,
            border_color=palette["border"],
        )

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=spacing("spacing_m"), pady=(spacing("spacing_s"), 2))

        ctk.CTkLabel(
            header,
            text=self._metric_type.display_name,
            font=make_font(size=12, weight="bold"),
            text_color=palette["text_primary"],
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text=f"({self._metric_type.unit})",
            font=make_font(size=10),
            text_color=palette["text_secondary"],
        ).pack(side="left", padx=(4, 0))

        if self._metrics:
            last = self._metrics[-1]
            info = f"{last.source_name} · {last.fetched_at.strftime('%Y-%m-%d')}"
            ctk.CTkLabel(
                header,
                text=info,
                font=make_font(size=9),
                text_color=palette["text_secondary"],
            ).pack(side="right")

        values_frame = ctk.CTkFrame(self, fg_color="transparent")
        values_frame.pack(fill="x", padx=spacing("spacing_m"), pady=(2, spacing("spacing_s")))

        for m in self._metrics:
            cell = ctk.CTkFrame(values_frame, fg_color="transparent", width=68)
            cell.pack(side="left", padx=spacing("spacing_s") // 4)
            cell.pack_propagate(False)

            ctk.CTkLabel(
                cell,
                text=m.period,
                font=make_font(size=8),
                text_color=palette["text_secondary"],
            ).pack()

            if m.is_unreported:
                ctk.CTkLabel(
                    cell,
                    text="未公告",
                    font=make_font(size=9),
                    text_color=palette["text_secondary"],
                ).pack()
            else:
                val_text = f"{m.value:.2f}" if m.value is not None else "—"
                ctk.CTkLabel(
                    cell,
                    text=val_text,
                    font=make_font(size=11),
                    text_color=palette["text_primary"],
                ).pack()

                if m.direction:
                    arrow = _DIRECTION_ARROWS[m.direction]
                    color_map = {
                        Direction.IMPROVING: palette["sentiment_positive"],
                        Direction.STABLE:    palette["text_secondary"],
                        Direction.DECLINING: palette["sentiment_negative"],
                    }
                    ctk.CTkLabel(
                        cell,
                        text=arrow,
                        font=make_font(size=11),
                        text_color=color_map[m.direction],
                    ).pack()
