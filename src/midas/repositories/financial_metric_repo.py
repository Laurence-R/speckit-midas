"""FinancialMetric repository implementation."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from midas.models.financial_metric import Direction, FinancialMetric, MetricType
from midas.repositories.interfaces import IFinancialMetricRepository


class FinancialMetricRepo(IFinancialMetricRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # IFinancialMetricRepository
    # ------------------------------------------------------------------

    def get_by_symbol(self, symbol: str) -> list[FinancialMetric]:
        rows = self._conn.execute(
            """
            SELECT * FROM financial_metrics
            WHERE symbol = ?
            ORDER BY metric_type ASC, period ASC
            """,
            (symbol,),
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def upsert_many(self, metrics: list[FinancialMetric]) -> None:
        self._conn.executemany(
            """
            INSERT INTO financial_metrics
                (symbol, metric_type, period, value, is_unreported,
                 direction, change_pct, source_name, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, metric_type, period) DO UPDATE SET
                value        = excluded.value,
                is_unreported = excluded.is_unreported,
                direction    = excluded.direction,
                change_pct   = excluded.change_pct,
                source_name  = excluded.source_name,
                fetched_at   = excluded.fetched_at
            """,
            [self._model_to_row(m) for m in metrics],
        )
        self._conn.commit()

    def is_cache_valid(self, symbol: str, ttl_days: int = 7) -> bool:
        """True if the most recent fetched_at for *symbol* is within *ttl_days*."""
        row = self._conn.execute(
            """
            SELECT MAX(fetched_at) AS last_fetched
            FROM financial_metrics
            WHERE symbol = ?
            """,
            (symbol,),
        ).fetchone()
        if not row or not row["last_fetched"]:
            return False
        last_fetched = datetime.fromisoformat(row["last_fetched"])
        return datetime.now() - last_fetched < timedelta(days=ttl_days)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _model_to_row(m: FinancialMetric) -> tuple:
        return (
            m.symbol,
            m.metric_type.value,
            m.period,
            m.value,
            int(m.is_unreported),
            m.direction.value if m.direction else None,
            m.change_pct,
            m.source_name,
            m.fetched_at.isoformat(),
        )

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> FinancialMetric:
        return FinancialMetric(
            id=row["id"],
            symbol=row["symbol"],
            metric_type=MetricType(row["metric_type"]),
            period=row["period"],
            value=row["value"],
            is_unreported=bool(row["is_unreported"]),
            direction=Direction(row["direction"]) if row["direction"] else None,
            change_pct=row["change_pct"],
            source_name=row["source_name"],
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
        )
