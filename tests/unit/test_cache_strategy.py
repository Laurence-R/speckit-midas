"""Unit tests for FinancialMetricRepo.is_cache_valid() cache strategy."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

import pytest

from midas.repositories.database import DatabaseManager
from midas.repositories.financial_metric_repo import FinancialMetricRepo
from midas.models.financial_metric import Direction, FinancialMetric, MetricType


@pytest.fixture()
def repo() -> FinancialMetricRepo:
    """Return a FinancialMetricRepo backed by an in-memory SQLite DB."""
    db = DatabaseManager(db_path=":memory:")
    db.init()
    conn = db.connect()
    return FinancialMetricRepo(conn)


def _make_metric(symbol: str, fetched_at: datetime) -> FinancialMetric:
    return FinancialMetric(
        symbol=symbol,
        metric_type=MetricType.PER,
        period="2025-Q4",
        value=5.0,
        is_unreported=False,
        source_name="FinMind",
        fetched_at=fetched_at,
    )


class TestIsCacheValid:
    def test_within_7_days_is_valid(self, repo: FinancialMetricRepo) -> None:
        recent = datetime.now() - timedelta(days=3)
        repo.upsert_many([_make_metric("2330", recent)])
        assert repo.is_cache_valid("2330") is True

    def test_exactly_7_days_is_expired(self, repo: FinancialMetricRepo) -> None:
        # 7 days ago → not strictly less than 7 days → invalid
        exactly_7 = datetime.now() - timedelta(days=7, seconds=1)
        repo.upsert_many([_make_metric("2330", exactly_7)])
        assert repo.is_cache_valid("2330") is False

    def test_over_7_days_is_expired(self, repo: FinancialMetricRepo) -> None:
        old = datetime.now() - timedelta(days=10)
        repo.upsert_many([_make_metric("2330", old)])
        assert repo.is_cache_valid("2330") is False

    def test_null_cache_is_invalid(self, repo: FinancialMetricRepo) -> None:
        # No rows inserted → cache is invalid
        assert repo.is_cache_valid("9999") is False

    def test_custom_ttl_respected(self, repo: FinancialMetricRepo) -> None:
        recent = datetime.now() - timedelta(days=2)
        repo.upsert_many([_make_metric("2330", recent)])
        # TTL = 1 day → expired
        assert repo.is_cache_valid("2330", ttl_days=1) is False
        # TTL = 3 days → still valid
        assert repo.is_cache_valid("2330", ttl_days=3) is True
