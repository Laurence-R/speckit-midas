"""MarketEvent repository implementation."""
from __future__ import annotations

import sqlite3
from datetime import datetime

from midas.models.market_event import EventType, MarketEvent, Sentiment
from midas.repositories.interfaces import IMarketEventRepository


class MarketEventRepo(IMarketEventRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # IMarketEventRepository
    # ------------------------------------------------------------------

    def get_by_date(self, date: str, symbols: list[str]) -> list[MarketEvent]:
        if not symbols:
            return []
        placeholders = ",".join("?" * len(symbols))
        rows = self._conn.execute(
            f"""
            SELECT * FROM market_events
            WHERE event_date = ? AND symbol IN ({placeholders})
            ORDER BY event_type_priority ASC, occurred_at DESC
            """,
            (date, *symbols),
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def get_by_symbol_date(self, symbol: str, date: str) -> list[MarketEvent]:
        rows = self._conn.execute(
            """
            SELECT * FROM market_events
            WHERE symbol = ? AND event_date = ?
            ORDER BY event_type_priority ASC, occurred_at DESC
            """,
            (symbol, date),
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def get_today_events_for_symbols(
        self, symbols: list[str], date: str
    ) -> list[MarketEvent]:
        return self.get_by_date(date, symbols)

    def upsert_many(self, events: list[MarketEvent]) -> None:
        """Upsert events and refresh mutable source fields on uniqueness conflicts."""
        self._conn.executemany(
            """
            INSERT INTO market_events (
                symbol, event_date, event_type, event_type_priority,
                occurred_at, title, source_url, source_name,
                ai_summary, ai_summary_generated_at, ai_model,
                sentiment, disclaimer, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, event_date, source_url) DO UPDATE SET
                event_type = excluded.event_type,
                event_type_priority = excluded.event_type_priority,
                occurred_at = excluded.occurred_at,
                title = excluded.title,
                source_name = excluded.source_name,
                fetched_at = excluded.fetched_at
            """,
            [self._model_to_row(e) for e in events],
        )
        self._conn.commit()

    def update_summary(self, event: MarketEvent) -> None:
        """Update AI summary, sentiment, and generated_at for an existing event."""
        self._conn.execute(
            """
            UPDATE market_events
            SET ai_summary = ?, sentiment = ?, ai_summary_generated_at = ?, ai_model = ?
            WHERE symbol = ? AND event_date = ? AND source_url = ?
            """,
            (
                event.ai_summary,
                event.sentiment.value if event.sentiment else None,
                event.ai_summary_generated_at.isoformat() if event.ai_summary_generated_at else None,
                event.ai_model,
                event.symbol,
                event.event_date,
                event.source_url,
            ),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _model_to_row(e: MarketEvent) -> tuple:
        return (
            e.symbol,
            e.event_date,
            e.event_type.value,
            e.event_type.priority,
            e.occurred_at.isoformat(),
            e.title,
            e.source_url,
            e.source_name,
            e.ai_summary,
            e.ai_summary_generated_at.isoformat() if e.ai_summary_generated_at else None,
            e.ai_model,
            e.sentiment.value if e.sentiment else None,
            e.disclaimer,
            e.fetched_at.isoformat(),
        )

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> MarketEvent:
        return MarketEvent(
            id=row["id"],
            symbol=row["symbol"],
            event_date=row["event_date"],
            event_type=EventType(row["event_type"]),
            occurred_at=datetime.fromisoformat(row["occurred_at"]),
            title=row["title"],
            source_url=row["source_url"],
            source_name=row["source_name"],
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            ai_summary=row["ai_summary"],
            ai_summary_generated_at=(
                datetime.fromisoformat(row["ai_summary_generated_at"])
                if row["ai_summary_generated_at"]
                else None
            ),
            ai_model=row["ai_model"],
            sentiment=Sentiment(row["sentiment"]) if row["sentiment"] else None,
            disclaimer=row["disclaimer"],
        )
