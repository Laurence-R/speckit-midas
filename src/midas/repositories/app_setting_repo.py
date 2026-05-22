"""App setting repository implementation."""
from __future__ import annotations

import sqlite3

from midas.repositories.interfaces import IAppSettingRepository


class AppSettingRepo(IAppSettingRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_value(self, key: str, default: str = "") -> str:
        row = self._conn.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (key,),
        ).fetchone()
        return row["value"] if row and row["value"] else default

    def set_value(self, key: str, value: str) -> None:
        self._conn.execute(
            """
            INSERT INTO app_settings(key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )
        self._conn.commit()

    def has_value(self, key: str) -> bool:
        return bool(self.get_value(key))