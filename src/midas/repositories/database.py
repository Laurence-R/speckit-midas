"""SQLite database initialisation and connection management."""
from __future__ import annotations

import sqlite3
from pathlib import Path


_SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tracked_stocks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT    NOT NULL UNIQUE,
    company_name TEXT    NOT NULL,
    added_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    memo         TEXT    NOT NULL DEFAULT '',
    sort_order   INTEGER NOT NULL DEFAULT 0,
    last_price             REAL,
    last_price_change_pct  REAL,
    last_price_date        TEXT
);

CREATE TABLE IF NOT EXISTS market_events (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol                  TEXT    NOT NULL,
    event_date              TEXT    NOT NULL,
    event_type              TEXT    NOT NULL,
    event_type_priority     INTEGER NOT NULL,
    occurred_at             DATETIME NOT NULL,
    title                   TEXT    NOT NULL,
    source_url              TEXT    NOT NULL,
    source_name             TEXT    NOT NULL,
    ai_summary              TEXT,
    ai_summary_generated_at DATETIME,
    ai_model                TEXT,
    sentiment               TEXT,
    disclaimer              TEXT    NOT NULL DEFAULT '此為 AI 摘要，僅供參考，不構成投資建議。',
    fetched_at              DATETIME NOT NULL,
    UNIQUE(symbol, event_date, source_url)
);

CREATE INDEX IF NOT EXISTS idx_market_events_symbol_date
    ON market_events(symbol, event_date);
CREATE INDEX IF NOT EXISTS idx_market_events_date_priority
    ON market_events(event_date, event_type_priority);

CREATE TABLE IF NOT EXISTS financial_metrics (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT    NOT NULL,
    metric_type  TEXT    NOT NULL,
    period       TEXT    NOT NULL,
    value        REAL,
    is_unreported INTEGER NOT NULL DEFAULT 0,
    direction    TEXT,
    change_pct   REAL,
    source_name  TEXT    NOT NULL,
    fetched_at   DATETIME NOT NULL,
    UNIQUE(symbol, metric_type, period)
);

CREATE INDEX IF NOT EXISTS idx_financial_metrics_symbol
    ON financial_metrics(symbol, metric_type, period);

CREATE TABLE IF NOT EXISTS market_overviews (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    trading_date     TEXT    NOT NULL UNIQUE,
    taiex_close      REAL    NOT NULL,
    taiex_change     REAL    NOT NULL,
    taiex_change_pct REAL    NOT NULL,
    volume_b         REAL    NOT NULL,
    volume_5d_avg_b  REAL,
    sector_rankings  TEXT    NOT NULL,
    institutional    TEXT    NOT NULL,
    source_name      TEXT    NOT NULL,
    fetched_at       DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS update_jobs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    triggered_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at     DATETIME,
    status           TEXT    NOT NULL DEFAULT 'running',
    total_steps      INTEGER NOT NULL DEFAULT 0,
    completed_steps  INTEGER NOT NULL DEFAULT 0,
    error_message    TEXT,
    llm_calls_made   INTEGER NOT NULL DEFAULT 0,
    llm_tokens_used  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS app_settings (
    key        TEXT    PRIMARY KEY,
    value      TEXT    NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_DEFAULT_SETTINGS: list[tuple[str, str]] = [
    ("theme", "dark"),
    ("finmind_token", ""),
    ("gemini_api_key", ""),
    ("last_update_date", ""),
    ("llm_daily_calls", "0"),
    ("llm_daily_date", ""),
    ("font_scale", "0"),
]


class DatabaseManager:
    """Manages the SQLite connection and schema initialisation."""

    USER_VERSION = 1

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            from midas.config import load_config
            cfg = load_config()
            db_path = cfg.db_path
        self._db_str: str = str(db_path)
        # For :memory: databases we keep a single persistent connection so that
        # all callers share the same in-memory DB (primarily used in tests).
        self._in_memory: bool = self._db_str == ":memory:"
        self._cached_conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def init(self) -> None:
        """Ensure the DB directory exists, create schema, and insert defaults."""
        if not self._in_memory:
            Path(self._db_str).parent.mkdir(parents=True, exist_ok=True)
        conn = self.connect()
        try:
            conn.executescript(_SCHEMA_SQL)
            self._set_user_version(conn)
            self._insert_default_settings(conn)
            self._apply_migrations(conn)
            conn.commit()
        finally:
            if not self._in_memory:
                conn.close()

    def connect(self) -> sqlite3.Connection:
        """Return a connection to the database.

        For file-based databases a fresh connection is returned each call.
        For :memory: databases the same connection is reused so that the schema
        (created in ``init``) remains visible to all callers.
        """
        if self._in_memory:
            if self._cached_conn is None:
                self._cached_conn = self._new_connection()
            return self._cached_conn
        return self._new_connection()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _new_connection(self) -> sqlite3.Connection:
        # check_same_thread=False is intentional: background update threads
        # use their own dedicated connection objects and do not share them with
        # the main thread, so cross-thread usage is safe.
        conn = sqlite3.connect(self._db_str, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _set_user_version(self, conn: sqlite3.Connection) -> None:
        conn.execute(f"PRAGMA user_version = {self.USER_VERSION}")

    def _insert_default_settings(self, conn: sqlite3.Connection) -> None:
        conn.executemany(
            "INSERT OR IGNORE INTO app_settings(key, value) VALUES (?, ?)",
            _DEFAULT_SETTINGS,
        )

    def _apply_migrations(self, conn: sqlite3.Connection) -> None:
        """Add new columns to existing tables (idempotent — safe to call every init)."""
        existing_cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(tracked_stocks)").fetchall()
        }
        new_cols = [
            ("last_price", "REAL"),
            ("last_price_change_pct", "REAL"),
            ("last_price_date", "TEXT"),
        ]
        for col_name, col_type in new_cols:
            if col_name not in existing_cols:
                conn.execute(
                    f"ALTER TABLE tracked_stocks ADD COLUMN {col_name} {col_type}"
                )
