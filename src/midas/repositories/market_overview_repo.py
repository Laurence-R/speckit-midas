"""MarketOverview repository implementation."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from midas.models.market_overview import MarketOverview
from midas.repositories.interfaces import IMarketOverviewRepository


class MarketOverviewRepo(IMarketOverviewRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # IMarketOverviewRepository
    # ------------------------------------------------------------------

    def get_by_date(self, date: str) -> MarketOverview | None:
        row = self._conn.execute(
            "SELECT * FROM market_overviews WHERE trading_date = ?", (date,)
        ).fetchone()
        return self._row_to_model(row) if row else None

    def get_latest(self) -> MarketOverview | None:
        row = self._conn.execute(
            "SELECT * FROM market_overviews WHERE taiex_close > 0"
            " ORDER BY trading_date DESC LIMIT 1"
        ).fetchone()
        return self._row_to_model(row) if row else None

    def upsert(self, overview: MarketOverview) -> None:
        self._conn.execute(
            """
            INSERT INTO market_overviews (
                trading_date, taiex_close, taiex_change, taiex_change_pct,
                volume_b, volume_5d_avg_b, sector_rankings, institutional,
                source_name, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(trading_date) DO UPDATE SET
                taiex_close      = excluded.taiex_close,
                taiex_change     = excluded.taiex_change,
                taiex_change_pct = excluded.taiex_change_pct,
                volume_b         = excluded.volume_b,
                volume_5d_avg_b  = excluded.volume_5d_avg_b,
                sector_rankings  = excluded.sector_rankings,
                institutional    = excluded.institutional,
                source_name      = excluded.source_name,
                fetched_at       = excluded.fetched_at
            """,
            (
                overview.trading_date,
                overview.taiex_close,
                overview.taiex_change,
                overview.taiex_change_pct,
                overview.volume_b,
                overview.volume_5d_avg_b,
                json.dumps(overview.sector_rankings, ensure_ascii=False),
                json.dumps(overview.institutional, ensure_ascii=False),
                overview.source_name,
                overview.fetched_at.isoformat(),
            ),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> MarketOverview:
        return MarketOverview(
            id=row["id"],
            trading_date=row["trading_date"],
            taiex_close=row["taiex_close"],
            taiex_change=row["taiex_change"],
            taiex_change_pct=row["taiex_change_pct"],
            volume_b=row["volume_b"],
            volume_5d_avg_b=row["volume_5d_avg_b"],
            sector_rankings=json.loads(row["sector_rankings"]),
            institutional=json.loads(row["institutional"]),
            source_name=row["source_name"],
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
        )
