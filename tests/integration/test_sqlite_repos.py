"""Integration tests for all SQLite repositories using in-memory DB.

Marked @pytest.mark.integration — run with:
    uv run pytest tests/integration/test_sqlite_repos.py -m integration
"""
from __future__ import annotations

from datetime import datetime

import pytest

from midas.models.financial_metric import Direction, FinancialMetric, MetricType
from midas.models.market_event import EventType, MarketEvent, Sentiment
from midas.models.market_overview import MarketOverview
from midas.models.tracked_stock import TrackedStock
from midas.models.update_job import JobStatus, UpdateJob
from midas.repositories.database import DatabaseManager
from midas.repositories.app_setting_repo import AppSettingRepo
from midas.repositories.financial_metric_repo import FinancialMetricRepo
from midas.repositories.market_event_repo import MarketEventRepo
from midas.repositories.market_overview_repo import MarketOverviewRepo
from midas.repositories.tracked_stock_repo import TrackedStockRepo
from midas.repositories.update_job_repo import UpdateJobRepo


@pytest.fixture()
def db() -> DatabaseManager:
    mgr = DatabaseManager(db_path=":memory:")
    mgr.init()
    return mgr


@pytest.fixture()
def conn(db: DatabaseManager):
    return db.connect()


# ---------------------------------------------------------------------------
# AppSettingRepo
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestAppSettingRepo:
    def test_get_value_and_has_value(self, conn) -> None:
        repo = AppSettingRepo(conn)
        assert repo.get_value("theme") == "dark"
        assert repo.has_value("theme") is True
        assert repo.has_value("finmind_token") is False

    def test_set_value_updates_existing_key(self, conn) -> None:
        repo = AppSettingRepo(conn)
        repo.set_value("theme", "light")
        assert repo.get_value("theme") == "light"


# ---------------------------------------------------------------------------
# TrackedStockRepo
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestTrackedStockRepo:
    def test_add_and_get_all(self, conn) -> None:
        repo = TrackedStockRepo(conn)
        stock = TrackedStock(symbol="2330", company_name="台積電")
        repo.add(stock)
        all_stocks = repo.get_all()
        assert len(all_stocks) == 1
        assert all_stocks[0].symbol == "2330"

    def test_add_ignores_duplicate(self, conn) -> None:
        repo = TrackedStockRepo(conn)
        s = TrackedStock(symbol="2330", company_name="台積電")
        repo.add(s)
        repo.add(s)  # duplicate — INSERT OR IGNORE
        assert repo.count() == 1

    def test_remove(self, conn) -> None:
        repo = TrackedStockRepo(conn)
        repo.add(TrackedStock(symbol="2330", company_name="台積電"))
        repo.remove("2330")
        assert repo.count() == 0

    def test_update_memo(self, conn) -> None:
        repo = TrackedStockRepo(conn)
        repo.add(TrackedStock(symbol="2330", company_name="台積電"))
        repo.update_memo("2330", "重要持股")
        stock = repo.get_by_symbol("2330")
        assert stock is not None
        assert stock.memo == "重要持股"

    def test_search_by_symbol_or_name(self, conn) -> None:
        repo = TrackedStockRepo(conn)
        repo.add(TrackedStock(symbol="2330", company_name="台積電"))
        repo.add(TrackedStock(symbol="2317", company_name="鴻海"))
        results = repo.search_by_symbol_or_name("積")
        assert len(results) == 1
        assert results[0].symbol == "2330"

    def test_get_by_symbol_not_found(self, conn) -> None:
        repo = TrackedStockRepo(conn)
        assert repo.get_by_symbol("9999") is None

    def test_update_price(self, conn) -> None:
        repo = TrackedStockRepo(conn)
        repo.add(TrackedStock(symbol="2330", company_name="台積電"))
        repo.update_price("2330", 980.0, 1.23, "2026-05-20")
        stock = repo.get_by_symbol("2330")
        assert stock is not None
        assert stock.last_price == pytest.approx(980.0)
        assert stock.last_price_change_pct == pytest.approx(1.23)
        assert stock.last_price_date == "2026-05-20"


# ---------------------------------------------------------------------------
# MarketEventRepo
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestMarketEventRepo:
    def _make_event(self, symbol: str = "2330", source_url: str = "https://example.com/1") -> MarketEvent:
        return MarketEvent(
            symbol=symbol,
            event_date="2026-05-19",
            event_type=EventType.FINANCIAL_REPORT,
            occurred_at=datetime(2026, 5, 19, 10, 0),
            title="2025 Q4 財報",
            source_url=source_url,
            source_name="公開資訊觀測站",
            fetched_at=datetime(2026, 5, 19, 16, 0),
        )

    def test_upsert_and_get(self, conn) -> None:
        repo = MarketEventRepo(conn)
        repo.upsert_many([self._make_event()])
        events = repo.get_by_symbol_date("2330", "2026-05-19")
        assert len(events) == 1
        assert events[0].title == "2025 Q4 財報"

    def test_upsert_ignores_duplicate(self, conn) -> None:
        repo = MarketEventRepo(conn)
        e = self._make_event()
        repo.upsert_many([e, e])  # same source_url → duplicate ignored
        assert len(repo.get_by_symbol_date("2330", "2026-05-19")) == 1

    def test_get_today_events_for_symbols(self, conn) -> None:
        repo = MarketEventRepo(conn)
        repo.upsert_many([self._make_event("2330"), self._make_event("2317", "https://example.com/2")])
        events = repo.get_today_events_for_symbols(["2330"], "2026-05-19")
        assert len(events) == 1

    def test_event_type_priority_ordering(self, conn) -> None:
        repo = MarketEventRepo(conn)
        e1 = self._make_event(source_url="https://a.com/1")
        e1.event_type = EventType.GENERAL_ANNOUNCEMENT  # priority 4
        e2 = self._make_event(source_url="https://a.com/2")
        e2.event_type = EventType.FINANCIAL_REPORT  # priority 1
        repo.upsert_many([e1, e2])
        events = repo.get_by_symbol_date("2330", "2026-05-19")
        assert events[0].event_type == EventType.FINANCIAL_REPORT


# ---------------------------------------------------------------------------
# FinancialMetricRepo
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestFinancialMetricRepo:
    def _make_metric(self, period: str = "2025-Q4") -> FinancialMetric:
        return FinancialMetric(
            symbol="2330",
            metric_type=MetricType.PER,
            period=period,
            value=10.5,
            is_unreported=False,
            source_name="FinMind",
            fetched_at=datetime(2026, 5, 19),
        )

    def test_upsert_and_get(self, conn) -> None:
        repo = FinancialMetricRepo(conn)
        repo.upsert_many([self._make_metric()])
        metrics = repo.get_by_symbol("2330")
        assert len(metrics) == 1
        assert metrics[0].value == pytest.approx(10.5)

    def test_upsert_updates_existing(self, conn) -> None:
        repo = FinancialMetricRepo(conn)
        repo.upsert_many([self._make_metric()])
        updated = self._make_metric()
        updated.value = 12.0
        repo.upsert_many([updated])
        metrics = repo.get_by_symbol("2330")
        assert metrics[0].value == pytest.approx(12.0)

    def test_unique_constraint_symbol_type_period(self, conn) -> None:
        repo = FinancialMetricRepo(conn)
        repo.upsert_many([self._make_metric("2025-Q3"), self._make_metric("2025-Q4")])
        assert len(repo.get_by_symbol("2330")) == 2


# ---------------------------------------------------------------------------
# MarketOverviewRepo
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestMarketOverviewRepo:
    def _make_overview(self) -> MarketOverview:
        return MarketOverview(
            trading_date="2026-05-19",
            taiex_close=21000.0,
            taiex_change=100.0,
            taiex_change_pct=0.48,
            volume_b=3500.0,
            sector_rankings=[{"rank": 1, "name": "半導體", "change_pct": 1.2, "direction": "up"}],
            institutional={"foreign_net_b": 150.0, "trust_net_b": -20.0, "dealer_net_b": 5.0},
            source_name="FinMind",
            fetched_at=datetime(2026, 5, 19, 16, 0),
        )

    def test_upsert_and_get_by_date(self, conn) -> None:
        repo = MarketOverviewRepo(conn)
        repo.upsert(self._make_overview())
        overview = repo.get_by_date("2026-05-19")
        assert overview is not None
        assert overview.taiex_close == pytest.approx(21000.0)

    def test_upsert_updates_existing(self, conn) -> None:
        repo = MarketOverviewRepo(conn)
        repo.upsert(self._make_overview())
        updated = self._make_overview()
        updated.taiex_close = 21500.0
        repo.upsert(updated)
        assert repo.get_latest().taiex_close == pytest.approx(21500.0)

    def test_get_latest_returns_most_recent(self, conn) -> None:
        repo = MarketOverviewRepo(conn)
        o1 = self._make_overview()
        o1.trading_date = "2026-05-18"
        o2 = self._make_overview()
        o2.trading_date = "2026-05-19"
        repo.upsert(o1)
        repo.upsert(o2)
        assert repo.get_latest().trading_date == "2026-05-19"


# ---------------------------------------------------------------------------
# UpdateJobRepo
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestUpdateJobRepo:
    def test_create_and_get_latest(self, conn) -> None:
        repo = UpdateJobRepo(conn)
        job = UpdateJob(total_steps=5)
        job_id = repo.create(job)
        latest = repo.get_latest()
        assert latest is not None
        assert latest.id == job_id
        assert latest.status == JobStatus.RUNNING

    def test_complete(self, conn) -> None:
        repo = UpdateJobRepo(conn)
        job_id = repo.create(UpdateJob(total_steps=5))
        repo.complete(job_id, llm_calls=3, llm_tokens=1500)
        latest = repo.get_latest()
        assert latest.status == JobStatus.SUCCESS
        assert latest.llm_calls_made == 3

    def test_fail(self, conn) -> None:
        repo = UpdateJobRepo(conn)
        job_id = repo.create(UpdateJob(total_steps=5))
        repo.fail(job_id, "Connection timeout")
        latest = repo.get_latest()
        assert latest.status == JobStatus.FAILED
        assert latest.error_message == "Connection timeout"

    def test_get_history_limit(self, conn) -> None:
        repo = UpdateJobRepo(conn)
        for _ in range(5):
            repo.create(UpdateJob())
        assert len(repo.get_history(limit=3)) == 3

    def test_get_latest_success_returns_most_recent_success(self, conn) -> None:
        repo = UpdateJobRepo(conn)
        first_id = repo.create(UpdateJob(total_steps=4))
        second_id = repo.create(UpdateJob(total_steps=4))
        repo.complete(first_id)
        repo.fail(second_id, "boom")
        third_id = repo.create(UpdateJob(total_steps=4))
        repo.complete(third_id)

        latest_success = repo.get_latest_success()
        assert latest_success is not None
        assert latest_success.id == third_id
