"""Unit tests for FinancialAgent metric calculation logic."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from midas.agents.financial_agent import (
    FinancialAgent,
    _calc_direction,
    _change_pct,
    _safe_div,
)
from midas.models.financial_metric import Direction, MetricType

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture()
def per_data() -> list[dict]:
    return json.loads((FIXTURES_DIR / "sample_finmind_per.json").read_text())


@pytest.fixture()
def revenue_data() -> list[dict]:
    return json.loads((FIXTURES_DIR / "sample_finmind_revenue.json").read_text())


@pytest.fixture()
def agent() -> FinancialAgent:
    return FinancialAgent.__new__(FinancialAgent)


# ---------------------------------------------------------------------------
# Direction rule tests
# ---------------------------------------------------------------------------

class TestCalcDirection:
    def test_improving_above_5pct(self) -> None:
        assert _calc_direction(5.1) == Direction.IMPROVING

    def test_stable_at_exactly_5pct(self) -> None:
        assert _calc_direction(5.0) == Direction.STABLE

    def test_stable_at_minus_5pct(self) -> None:
        assert _calc_direction(-5.0) == Direction.STABLE

    def test_declining_below_minus_5pct(self) -> None:
        assert _calc_direction(-5.1) == Direction.DECLINING

    def test_none_returns_none(self) -> None:
        assert _calc_direction(None) is None

    def test_zero_is_stable(self) -> None:
        assert _calc_direction(0.0) == Direction.STABLE


class TestChangePct:
    def test_positive_change(self) -> None:
        result = _change_pct(110.0, 100.0)
        assert result == pytest.approx(10.0)

    def test_negative_change(self) -> None:
        result = _change_pct(90.0, 100.0)
        assert result == pytest.approx(-10.0)

    def test_zero_previous_returns_none(self) -> None:
        assert _change_pct(100.0, 0.0) is None

    def test_none_current_returns_none(self) -> None:
        assert _change_pct(None, 100.0) is None

    def test_none_previous_returns_none(self) -> None:
        assert _change_pct(100.0, None) is None


class TestSafeDiv:
    def test_basic_division(self) -> None:
        assert _safe_div(100.0, 200.0) == pytest.approx(50.0)

    def test_zero_denominator_returns_none(self) -> None:
        assert _safe_div(100.0, 0.0) is None

    def test_none_numerator_returns_none(self) -> None:
        assert _safe_div(None, 200.0) is None

    def test_none_denominator_returns_none(self) -> None:
        assert _safe_div(100.0, None) is None


# ---------------------------------------------------------------------------
# PER metric calculation tests (_calc_per_metrics)
# ---------------------------------------------------------------------------

class TestCalcPerMetrics:
    def test_returns_3_metrics_per_month(
        self, agent: FinancialAgent, per_data: list[dict]
    ) -> None:
        # fixture: Jan-15, Jan-31, Feb-28, Mar-29, Apr-30, May-31(null)
        # → 5 unique months, 3 metrics each = 15
        metrics = agent._calc_per_metrics(per_data, "2330")
        assert len(metrics) == 5 * 3

    def test_january_uses_latest_daily_record(
        self, agent: FinancialAgent, per_data: list[dict]
    ) -> None:
        """Jan has two records (15th and 31st); the 31st should be used."""
        metrics = agent._calc_per_metrics(per_data, "2330")
        jan_per = next(
            m for m in metrics
            if m.metric_type == MetricType.PER and m.period == "2024-01"
        )
        assert jan_per.value == pytest.approx(25.5)  # from Jan-31 record

    def test_null_month_marked_unreported(
        self, agent: FinancialAgent, per_data: list[dict]
    ) -> None:
        metrics = agent._calc_per_metrics(per_data, "2330")
        unreported = [m for m in metrics if m.is_unreported]
        assert len(unreported) == 3  # 1 null month × 3 metric types

    def test_first_month_has_no_direction(
        self, agent: FinancialAgent, per_data: list[dict]
    ) -> None:
        metrics = agent._calc_per_metrics(per_data, "2330")
        first_per = next(
            m for m in metrics
            if m.metric_type == MetricType.PER and m.period == "2024-01"
        )
        assert first_per.direction is None
        assert first_per.change_pct is None

    def test_period_format_is_year_month(
        self, agent: FinancialAgent, per_data: list[dict]
    ) -> None:
        metrics = agent._calc_per_metrics(per_data, "2330")
        periods = {m.period for m in metrics}
        assert "2024-01" in periods
        assert "2024-04" in periods

    def test_second_month_direction_calculated(
        self, agent: FinancialAgent, per_data: list[dict]
    ) -> None:
        """Feb PER (26.0) vs Jan PER (25.5) → ~+2% → STABLE."""
        metrics = agent._calc_per_metrics(per_data, "2330")
        feb_per = next(
            m for m in metrics
            if m.metric_type == MetricType.PER and m.period == "2024-02"
        )
        assert feb_per.direction == Direction.STABLE
        assert feb_per.change_pct is not None


# ---------------------------------------------------------------------------
# Revenue metric calculation tests (_calc_revenue_metrics)
# ---------------------------------------------------------------------------

class TestCalcRevenueMetrics:
    def test_returns_2_metrics_per_month(
        self, agent: FinancialAgent, revenue_data: list[dict]
    ) -> None:
        # fixture: 4 months → 4 × 2 = 8 metrics
        metrics = agent._calc_revenue_metrics(revenue_data, "2330")
        assert len(metrics) == 4 * 2

    def test_monthly_revenue_converted_to_yi(
        self, agent: FinancialAgent, revenue_data: list[dict]
    ) -> None:
        """2023-01 revenue = 188500000000 (actual NTD) → 1885.0 億元."""
        metrics = agent._calc_revenue_metrics(revenue_data, "2330")
        jan_rev = next(
            m for m in metrics
            if m.metric_type == MetricType.MONTHLY_REVENUE and m.period == "2023-01"
        )
        assert jan_rev.value == pytest.approx(1885.0)

    def test_revenue_yoy_calculated_when_year_ago_available(
        self, agent: FinancialAgent, revenue_data: list[dict]
    ) -> None:
        """2024-01: (213500000000 - 188500000000) / 188500000000 × 100 ≈ 13.26%."""
        metrics = agent._calc_revenue_metrics(revenue_data, "2330")
        jan24_yoy = next(
            m for m in metrics
            if m.metric_type == MetricType.REVENUE_YOY and m.period == "2024-01"
        )
        assert jan24_yoy.value == pytest.approx(25_000_000 / 188_500_000 * 100)
        assert jan24_yoy.is_unreported is False

    def test_revenue_yoy_none_when_no_year_ago(
        self, agent: FinancialAgent, revenue_data: list[dict]
    ) -> None:
        """2023-01 has no year-ago data → YoY value is None, not unreported."""
        metrics = agent._calc_revenue_metrics(revenue_data, "2330")
        jan23_yoy = next(
            m for m in metrics
            if m.metric_type == MetricType.REVENUE_YOY and m.period == "2023-01"
        )
        assert jan23_yoy.value is None
        assert jan23_yoy.is_unreported is False

    def test_first_month_revenue_has_no_direction(
        self, agent: FinancialAgent, revenue_data: list[dict]
    ) -> None:
        metrics = agent._calc_revenue_metrics(revenue_data, "2330")
        jan23_rev = next(
            m for m in metrics
            if m.metric_type == MetricType.MONTHLY_REVENUE and m.period == "2023-01"
        )
        assert jan23_rev.direction is None
        assert jan23_rev.change_pct is None

    def test_period_format_is_year_month(
        self, agent: FinancialAgent, revenue_data: list[dict]
    ) -> None:
        metrics = agent._calc_revenue_metrics(revenue_data, "2330")
        periods = {m.period for m in metrics}
        assert "2023-01" in periods
        assert "2024-02" in periods

