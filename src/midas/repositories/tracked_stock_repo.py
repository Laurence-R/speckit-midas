"""TrackedStock repository implementation."""
from __future__ import annotations

import sqlite3
from datetime import datetime

from midas.models.tracked_stock import TrackedStock
from midas.repositories.interfaces import ITrackedStockRepository


class TrackedStockRepo(ITrackedStockRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # ITrackedStockRepository
    # ------------------------------------------------------------------

    def get_all(self) -> list[TrackedStock]:
        rows = self._conn.execute(
            "SELECT * FROM tracked_stocks ORDER BY sort_order ASC, added_at ASC"
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def get_by_symbol(self, symbol: str) -> TrackedStock | None:
        row = self._conn.execute(
            "SELECT * FROM tracked_stocks WHERE symbol = ?", (symbol,)
        ).fetchone()
        return self._row_to_model(row) if row else None

    def add(self, stock: TrackedStock) -> None:
        """INSERT OR IGNORE prevents overwriting added_at on duplicate symbol."""
        self._conn.execute(
            """
            INSERT OR IGNORE INTO tracked_stocks
                (symbol, company_name, added_at, memo, sort_order)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                stock.symbol,
                stock.company_name,
                stock.added_at.isoformat(),
                stock.memo,
                stock.sort_order,
            ),
        )
        self._conn.commit()

    def remove(self, symbol: str) -> None:
        self._conn.execute(
            "DELETE FROM tracked_stocks WHERE symbol = ?", (symbol,)
        )
        self._conn.commit()

    def update_memo(self, symbol: str, memo: str) -> None:
        self._conn.execute(
            "UPDATE tracked_stocks SET memo = ? WHERE symbol = ?",
            (memo, symbol),
        )
        self._conn.commit()

    def update_price(
        self,
        symbol: str,
        last_price: float,
        last_price_change_pct: float | None,
        last_price_date: str,
    ) -> None:
        self._conn.execute(
            """
            UPDATE tracked_stocks
               SET last_price = ?, last_price_change_pct = ?, last_price_date = ?
             WHERE symbol = ?
            """,
            (last_price, last_price_change_pct, last_price_date, symbol),
        )
        self._conn.commit()

    def count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM tracked_stocks"
        ).fetchone()
        return int(row[0])

    def search_by_symbol_or_name(self, query: str) -> list[TrackedStock]:
        pattern = f"%{query}%"
        rows = self._conn.execute(
            """
            SELECT * FROM tracked_stocks
            WHERE symbol LIKE ? OR company_name LIKE ?
            ORDER BY sort_order ASC, added_at ASC
            """,
            (pattern, pattern),
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> TrackedStock:
        return TrackedStock(
            id=row["id"],
            symbol=row["symbol"],
            company_name=row["company_name"],
            added_at=datetime.fromisoformat(row["added_at"]),
            memo=row["memo"],
            sort_order=row["sort_order"],
            last_price=row["last_price"] if row["last_price"] is not None else None,
            last_price_change_pct=row["last_price_change_pct"] if row["last_price_change_pct"] is not None else None,
            last_price_date=row["last_price_date"],
        )
