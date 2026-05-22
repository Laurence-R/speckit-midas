"""Financial agent: fetches FinMind PER/revenue data and calculates 5 free-tier metrics."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from midas.agents.interfaces import IFinancialAgent
from midas.integrations.finmind_client import FinMindClient
from midas.models.financial_metric import Direction, FinancialMetric, MetricType

logger = logging.getLogger(__name__)

# Fetch data covering ~2 years for trend analysis
_LOOKBACK_DAYS = 730  # ~2 years

# Direction thresholds
_IMPROVING_THRESHOLD = 5.0  # change_pct > +5% → improving
_DECLINING_THRESHOLD = -5.0  # change_pct < -5% → declining


def _calc_direction(change_pct: float | None) -> Direction | None:
    """Return direction label based on ±5% rule."""
    if change_pct is None:
        return None
    if change_pct > _IMPROVING_THRESHOLD:
        return Direction.IMPROVING
    if change_pct < _DECLINING_THRESHOLD:
        return Direction.DECLINING
    return Direction.STABLE


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    """Return numerator/denominator×100, or None if either value is missing/zero."""
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return numerator / denominator * 100


def _change_pct(current: float | None, previous: float | None) -> float | None:
    """Return % change from *previous* to *current*, or None if unavailable."""
    if current is None or previous is None:
        return None
    if previous == 0:
        return None
    return (current - previous) / abs(previous) * 100


class FinancialAgent(IFinancialAgent):
    """Fetches FinMind PER/monthly-revenue data (free tier) and calculates 5 metrics."""

    def __init__(self, finmind_client: FinMindClient | None = None) -> None:
        self._client = finmind_client or FinMindClient()

    # ------------------------------------------------------------------
    # IFinancialAgent
    # ------------------------------------------------------------------

    def fetch_and_calculate(self, symbol: str) -> list[FinancialMetric]:
        """Fetch PER and monthly revenue data and calculate all 5 free-tier metrics.

        Returns an empty list if the API call fails.
        """
        start_date = (datetime.now() - timedelta(days=_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
        try:
            per_raw = self._client.get_per_pbr(symbol, start_date)
            rev_raw = self._client.get_monthly_revenue(symbol, start_date)
        except Exception as exc:  # noqa: BLE001
            logger.warning("FinancialAgent: failed to fetch data for %s: %s", symbol, exc)
            return []

        metrics: list[FinancialMetric] = []
        metrics.extend(self._calc_per_metrics(per_raw.get("data", []), symbol))
        metrics.extend(self._calc_revenue_metrics(rev_raw.get("data", []), symbol))
        return metrics

    # ------------------------------------------------------------------
    # Internal: PER / PBR / dividend yield  (TaiwanStockPER, daily → grouped monthly)
    # ------------------------------------------------------------------

    def _calc_per_metrics(
        self, per_data: list[dict[str, Any]], symbol: str
    ) -> list[FinancialMetric]:
        """Calculate PER, PBR, DIVIDEND_YIELD from TaiwanStockPER daily data.

        Groups records by year-month, keeps the latest record per month.
        Processes up to the last 24 months, sorted ascending for trend calculation.
        """
        # Group daily rows by "YYYY-MM", keep row with the latest date
        monthly: dict[str, dict[str, Any]] = {}
        for row in per_data:
            date_str: str = row.get("date", "")
            if not date_str:
                continue
            ym = date_str[:7]
            if ym not in monthly or date_str > monthly[ym].get("date", ""):
                monthly[ym] = row

        current_ym = datetime.now().strftime("%Y-%m")
        sorted_periods = [ym for ym in sorted(monthly.keys()) if ym < current_ym][-24:]
        fetched_at = datetime.now()
        metrics: list[FinancialMetric] = []

        per_mapping: list[tuple[MetricType, str]] = [
            (MetricType.PER, "PER"),
            (MetricType.PBR, "PBR"),
            (MetricType.DIVIDEND_YIELD, "dividend_yield"),
        ]
        prev_values: dict[MetricType, float | None] = {t: None for t, _ in per_mapping}

        for ym in sorted_periods:
            row = monthly[ym]
            is_unreported = all(row.get(f) is None for _, f in per_mapping)

            for metric_type, field in per_mapping:
                value = row.get(field) if not is_unreported else None
                prev = prev_values[metric_type]
                cpct = _change_pct(value, prev)
                direction = _calc_direction(cpct)

                metrics.append(
                    FinancialMetric(
                        symbol=symbol,
                        metric_type=metric_type,
                        period=ym,
                        value=value,
                        is_unreported=is_unreported,
                        direction=direction,
                        change_pct=cpct,
                        source_name="FinMind",
                        fetched_at=fetched_at,
                    )
                )
                prev_values[metric_type] = value

        return metrics

    # ------------------------------------------------------------------
    # Internal: monthly revenue  (TaiwanStockMonthRevenue, already monthly)
    # ------------------------------------------------------------------

    def _calc_revenue_metrics(
        self, rev_data: list[dict[str, Any]], symbol: str
    ) -> list[FinancialMetric]:
        """Calculate MONTHLY_REVENUE (億元) and REVENUE_YOY (%) from TaiwanStockMonthRevenue.

        Revenue values from FinMind are in actual NTD.
        Divides by 1e8 (100,000,000) to convert to 億元.
        Processes up to the last 24 months, sorted ascending.
        """
        # Build month → raw revenue (thousands NTD) lookup
        monthly_raw: dict[str, float | None] = {}
        for row in rev_data:
            date_str: str = row.get("date", "")
            if not date_str:
                continue
            ym = date_str[:7]
            rev = row.get("revenue")
            monthly_raw[ym] = float(rev) if rev is not None else None

        current_ym = datetime.now().strftime("%Y-%m")
        sorted_periods = [ym for ym in sorted(monthly_raw.keys()) if ym < current_ym][-24:]
        fetched_at = datetime.now()
        metrics: list[FinancialMetric] = []
        prev_raw: float | None = None

        for ym in sorted_periods:
            raw = monthly_raw.get(ym)

            # --- MONTHLY_REVENUE (億元) ---
            rev_yi = raw / 1e8 if raw is not None else None  # actual NTD → 億元
            cpct = _change_pct(raw, prev_raw)
            metrics.append(
                FinancialMetric(
                    symbol=symbol,
                    metric_type=MetricType.MONTHLY_REVENUE,
                    period=ym,
                    value=rev_yi,
                    is_unreported=(raw is None),
                    direction=_calc_direction(cpct),
                    change_pct=cpct,
                    source_name="FinMind",
                    fetched_at=fetched_at,
                )
            )
            prev_raw = raw

            # --- REVENUE_YOY (%) — value itself is the % change ---
            year_ago_ym = f"{int(ym[:4]) - 1}-{ym[5:]}"
            rev_year_ago = monthly_raw.get(year_ago_ym)
            yoy = _change_pct(raw, rev_year_ago)
            metrics.append(
                FinancialMetric(
                    symbol=symbol,
                    metric_type=MetricType.REVENUE_YOY,
                    period=ym,
                    value=yoy,
                    is_unreported=False,
                    direction=_calc_direction(yoy),
                    change_pct=None,  # value itself is already a % change
                    source_name="FinMind",
                    fetched_at=fetched_at,
                )
            )

        return metrics
